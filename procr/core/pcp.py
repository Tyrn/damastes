#!/usr/bin/env python

import sys

if sys.version_info < (3, 4, 0):
    sys.stderr.write("You need python 3.4 or later to run this script\n")
    sys.exit(1)

from mutagen import File
import os
import re
import shutil
import argparse
import warnings
import itertools as it
import functools as ft

utility_description = '''
pcp "Procrustes" SmArT is a CLI utility for copying subtrees containing supported audio
files in sequence, naturally sorted.
The end result is a "flattened" copy of the source subtree. "Flattened" means
that only a namesake of the root source directory is created, where all the files get
copied to, names prefixed with a serial number. Tags "Track" and "Tracks Total"
get set, tags "Artist" and "Album" can be replaced optionally.
The writing process is strictly sequential: either starting with the number one file,
or in the reversed order. This can be important for some mobile devices.
'''


def sans_ext(s):
    """
    Discards file extension
    """
    root, ext = os.path.splitext(s)
    return root


def str_strip_numbers(s):
    """
    Returns a vector of integer numbers
    embedded in a string argument
    """
    return [int(x) for x in re.compile('\d+').findall(s)]


def cmpv_int(vx, vy):
    """
    Compares vectors of integers using 'string semantics'
    """
    nonzero_tail = list(it.dropwhile(lambda x: x == 0, [x[0] - x[1] for x in zip(vx, vy)]))
    return len(vx) - len(vy) if nonzero_tail == [] else -1 if nonzero_tail[0] < 0 else 1


def cmpstr_c(x, y):
    return 0 if x == y else -1 if x < y else 1


def cmpstr_naturally(str_x, str_y):
    """
    If both strings contain digits, returns numerical comparison based on the numeric
    values embedded in the strings, otherwise returns the standard string comparison.
    The idea of the natural sort as opposed to the standard lexicographic sort is one of coping
    with the possible absence of the leading zeros in 'numbers' of files or directories
    """
    num_x = str_strip_numbers(str_x)
    num_y = str_strip_numbers(str_y)
    return cmpv_int(num_x, num_y) if num_x != [] and num_y != [] else cmpstr_c(str_x, str_y)


def compare_path(xp, yp):
    """
    Compares two paths, ignoring extensions
    """
    x = sans_ext(xp)
    y = sans_ext(yp)
    return cmpstr_c(x, y) if args.sort_lex else cmpstr_naturally(x, y)


def compare_file(xf, yf):
    """
    Compares two paths, filenames only, ignoring extensions
    """
    x = sans_ext(os.path.basename(xf))
    y = sans_ext(os.path.basename(yf))
    return cmpstr_c(x, y) if args.sort_lex else cmpstr_naturally(x, y)


def mutagen_file(x):
    """
    Returns Mutagen thing, if x is looks like audio file path, else returns None
    """
    return File(x, easy=True)


def isaudiofile(x):
    """
    Returns True, if x is an audio file, else returns False
    """
    return not os.path.isdir(x) and mutagen_file(x) is not None


def list_dir_groom(abs_path, rev=False):
    """
    Returns a tuple of: (0) naturally sorted list of
    offspring directory paths (1) naturally sorted list
    of offspring file paths.
    """
    lst = [os.path.join(abs_path, x) for x in os.listdir(abs_path)]
    dirs = sorted([x for x in lst if os.path.isdir(x)],
                  key=ft.cmp_to_key((lambda xp, yp: -compare_path(xp, yp)) if rev else compare_path))
    files = sorted([x for x in lst if isaudiofile(x)],
                   key=ft.cmp_to_key((lambda xf, yf: -compare_file(xf, yf)) if rev else compare_file))
    return dirs, files


args = None


def decorate_dir_name(i, name):
    return str(i).zfill(3) + "-" + name


def decorate_file_name(cntw, i, name):
    global args
    root, ext = os.path.splitext(name)
    return str(i).zfill(cntw) + "-" + (name if args.unified_name is None else args.unified_name + ext)


def traverse_tree_dst(src_dir, dst_root, dst_step, cntw):
    """
    Recursively traverses the source directory and yields a sequence of (src, tree dst) pairs;
    the destination directory and file names get decorated according to options
    """
    dirs, files = list_dir_groom(src_dir)

    for i, d in enumerate(dirs):
        step = os.path.join(dst_step, decorate_dir_name(i, os.path.basename(d)))
        os.mkdir(os.path.join(dst_root, step))
        yield from traverse_tree_dst(d, dst_root, step, cntw)

    for i, f in enumerate(files):
        dst_path = os.path.join(dst_root, os.path.join(dst_step, decorate_file_name(cntw, i, os.path.basename(f))))
        yield f, dst_path


def traverse_flat_dst(src_dir, dst_root, fcount, cntw):
    """
    Recursively traverses the source directory and yields a sequence of (src, flat dst) pairs;
    the destination directory and file names get decorated according to options
    """
    dirs, files = list_dir_groom(src_dir)

    for i, d in enumerate(dirs):
        yield from traverse_flat_dst(d, dst_root, fcount, cntw)

    for i, f in enumerate(files):
        dst_path = os.path.join(dst_root, decorate_file_name(cntw, fcount[0], os.path.basename(f)))
        fcount[0] += 1
        yield f, dst_path


def traverse_flat_dst_r(src_dir, dst_root, fcount, cntw):
    """
    Recursively traverses the source directory backwards (-r) and yields a sequence of (src, flat dst) pairs;
    the destination directory and file names get decorated according to options
    """
    dirs, files = list_dir_groom(src_dir, rev=True)

    for i, f in enumerate(files):
        dst_path = os.path.join(dst_root, decorate_file_name(cntw, fcount[0], os.path.basename(f)))
        fcount[0] -= 1
        yield f, dst_path

    for i, d in enumerate(dirs):
        yield from traverse_flat_dst_r(d, dst_root, fcount, cntw)


def groom(src, dst, cnt):
    """
    Makes an 'executive' run of traversing the source directory; returns the 'ammo belt' generator
    """
    global args
    cntw = len(str(cnt))      # File number substring need not be wider than this

    if args.tree_dst:
        return traverse_tree_dst(src, dst, "", cntw)
    else:
        if args.reverse:
            return traverse_flat_dst_r(src, dst, [cnt], cntw)
        else:
            return traverse_flat_dst(src, dst, [1], cntw)


def build_album():
    """
    Sets up boilerplate required by the options and returns the ammo belt generator
    of (src, dst) pairs
    """
    global args
    src_name = os.path.basename(args.src_dir)
    prefix = "" if args.album_num is None else (str(args.album_num).zfill(2) + "-")
    base_dst = prefix + (src_name if args.unified_name is None else args.unified_name)
    executive_dst = os.path.join(args.dst_dir, "" if args.drop_dst else base_dst)

    def audiofiles_count(dir):
        """
        Returns full recursive count of audiofiles in dir
        """
        cnt = 0

        for root, dirs, files in os.walk(dir):
            for name in files:
                if isaudiofile(os.path.join(root, name)):
                    cnt += 1
        return cnt

    if not args.drop_dst:
        if os.path.exists(executive_dst):
            print('Destination directory "{}" already exists.'.format(executive_dst))
            sys.exit()
        else:
            os.mkdir(executive_dst)

    tot = audiofiles_count(args.src_dir)
    belt = groom(args.src_dir, executive_dst, tot)

    if not args.drop_dst and tot == 0:
        shutil.rmtree(executive_dst)
        print('There are no supported audio files in the source directory "{}".'.format(args.src_dir))
        sys.exit()

    return tot, belt


def make_initials(name, separator):
    """
    Reduces a string of names to initials. Trailing separator is not appended
    """
    return separator.join(x[0] for x in re.split("\s+", name)).upper()


def copy_album():
    """
    Runs through the ammo belt and does copying, in the reverse order if necessary
    """
    global args

    def _set_tags(i, total, path, title):
        audio = mutagen_file(path)
        if audio is None:
            return
        audio["tracknumber"] = str(i) + "/" + str(total)
        if args.artist_tag is not None and args.album_tag is not None:
            audio["title"] = str(i) + " " + make_initials(args.artist_tag, ".") + ". - " + args.album_tag if title is None else title
            audio["artist"] = args.artist_tag
            audio["album"] = args.album_tag
        elif args.artist_tag is not None:
            audio["title"] = str(i) + " " + args.artist_tag if title is None else title
            audio["artist"] = args.artist_tag
        elif args.album_tag is not None:
            audio["title"] = str(i) + " " + args.album_tag if title is None else title
            audio["album"] = args.album_tag
        audio.save()

    def _cp(i, total, entry):
        src, dst = entry
        shutil.copy(src, dst)
        _set_tags(i, total, dst, sans_ext(os.path.basename(dst)) if args.file_title else None)
        print("{:>4}/{:<4} {}".format(i, total, dst))

    tot, belt = build_album()

    if args.reverse:
        for i, x in enumerate(belt):
            _cp(tot - i, tot, x)
    else:
        for i, x in enumerate(belt):
            _cp(i + 1, tot, x)


def retrieve_args():
    parser = argparse.ArgumentParser(description=utility_description)
    parser.add_argument("-f", "--file-title", help="use file name for title tag",
                        action="store_true")
    parser.add_argument("-x", "--sort-lex", help="sort files lexicographically",
                        action="store_true")
    parser.add_argument("-t", "--tree-dst", help="retain the tree structure of the source album at destination",
                        action="store_true")
    parser.add_argument("-p", "--drop-dst", help="do not create destination directory",
                        action="store_true")
    parser.add_argument("-r", "--reverse", help="copy files in reverse order (number one file is the last to be copied)",
                        action="store_true")
    parser.add_argument("-u", "--unified-name",
                        help='''
                        destination root directory name and file names are based on UNIFIED_NAME,
                        serial number prepended, file extensions retained
                        ''')
    parser.add_argument("-b", "--album-num", help="0..99; prepend ALBUM_NUM to the destination root directory name")
    parser.add_argument("-a", "--artist-tag", help="artist tag name")
    parser.add_argument("-g", "--album-tag", help="album tag name")
    parser.add_argument('src_dir', help="source directory")
    parser.add_argument('dst_dir', help="general destination directory")
    rg = parser.parse_args()
    rg.src_dir = os.path.abspath(rg.src_dir)    # Takes care of the trailing slash, too
    rg.dst_dir = os.path.abspath(rg.dst_dir)

    if rg.tree_dst and rg.reverse:
        print("  *** -t option ignored (conflicts with -r) ***")
        rg.tree_dst = False

    return rg


def main():
    global args

    try:
        warnings.resetwarnings()
        warnings.simplefilter('ignore')

        args = retrieve_args()
        copy_album()
    except KeyboardInterrupt as e:
        sys.exit(e)


if __name__ == '__main__':
        main()
