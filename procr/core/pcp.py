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
files in sequence (preorder of the source subtree, naturally sorted).
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
    return cmpstr_naturally(sans_ext(xp), sans_ext(yp))


def compare_file(xf, yf):
    """
    Compares two paths, filenames only, ignoring extensions
    """
    return cmpstr_naturally(sans_ext(os.path.basename(xf)), sans_ext(os.path.basename(yf)))


def list_dir_groom(abs_path):
    """
    Returns a tuple of: (0) naturally sorted list of
    offspring directory paths (1) naturally sorted list
    of offspring file paths.
    """
    def isaudiofile(x):
        return not os.path.isdir(x) and File(x, easy=True) is not None

    lst = [os.path.join(abs_path, x) for x in os.listdir(abs_path)]
    dirs = sorted([x for x in lst if os.path.isdir(x)], key=ft.cmp_to_key(compare_path))
    files = sorted([x for x in lst if isaudiofile(x)], key=ft.cmp_to_key(compare_file))
    return (dirs, files)


args = None
fcount = 0                # File counter: mutable by design!


def decorate_dir_name(i, name):
    return str(i).zfill(3) + "-" + name


def decorate_file_name(i, name):
    global args
    root, ext = os.path.splitext(name)
    return str(i).zfill(4) + "-" + (name if args.unified_name is None else args.unified_name + ext)


def traverse_tree_dst(src_dir, dst_root, dst_step):
    """
    Recursively traverses the source directory and yields a sequence of (src, tree dst) pairs;
    the destination directory and file names get decorated according to options
    MODIFIES fcount
    """
    global fcount
    dirs, files = list_dir_groom(src_dir)

    for i, d in enumerate(dirs):
        step = os.path.join(dst_step, decorate_dir_name(i, os.path.basename(d)))
        os.mkdir(os.path.join(dst_root, step))
        yield from traverse_tree_dst(d, dst_root, step)

    for i, f in enumerate(files):
        dst_path = os.path.join(dst_root, os.path.join(dst_step, decorate_file_name(i, os.path.basename(f))))
        fcount += 1
        yield (f, dst_path)


def traverse_flat_dst(src_dir, dst_root):
    """
    Recursively traverses the source directory and yields a sequence of (src, flat dst) pairs;
    the destination directory and file names get decorated according to options
    MODIFIES fcount
    """
    global fcount
    dirs, files = list_dir_groom(src_dir)

    for i, d in enumerate(dirs):
        yield from traverse_flat_dst(d, dst_root)

    for i, f in enumerate(files):
        dst_path = os.path.join(dst_root, decorate_file_name(fcount, os.path.basename(f)))
        fcount += 1
        yield (f, dst_path)


def groom(src, dst):
    """
    Makes an 'executive' run of traversing the source directory
    MODIFIES fcount
    """
    global args, fcount
    fcount = 1
    return list(traverse_tree_dst(src, dst, "") if args.tree_dst else traverse_flat_dst(src, dst))


def build_album():
    """
    Sets up boilerplate required by the options and returns the ammo belt
    (flat list of (src, dst) pairs)
    """
    global args
    src_name = os.path.basename(args.src_dir)
    prefix = "" if args.album_num is None else (str(args.album_num).zfill(2) + "-")
    base_dst = prefix + (src_name if args.unified_name is None else args.unified_name)
    executive_dst = os.path.join(args.dst_dir, "" if args.drop_dst else base_dst)

    if not args.drop_dst:
        if os.path.exists(executive_dst):
            print('Destination directory "{}" already exists.'.format(executive_dst))
            sys.exit()
        else:
            os.mkdir(executive_dst)

    belt = groom(args.src_dir, executive_dst)

    if not args.drop_dst and belt == []:
        shutil.rmtree(executive_dst)
        print('There are no supported audio files in the source directory "{}".'.format(args.src_dir))
        sys.exit()

    return belt


def make_initials(name, separator):
    """
    Reduces a string of names to initials. Trailing separator is not appended
    """
    return separator.join([x[0] for x in re.split("\s+", name)]).upper()


def copy_album():
    """
    Runs through the ammo belt and does copying, in the reverse order if necessary
    """
    global args, fcount
    belt = reversed(build_album()) if args.reverse else build_album()

    def _set_tags(i, total, path):
        audio = File(path, easy=True)
        if audio is None:
            return
        audio["tracknumber"] = str(i) + "/" + str(total)
        if args.artist_tag is not None and args.album_tag is not None:
            audio["title"] = str(i) + " " + make_initials(args.artist_tag, ".") + ". - " + args.album_tag
            audio["artist"] = args.artist_tag
            audio["album"] = args.album_tag
        elif args.artist_tag is not None:
            audio["title"] = str(i) + " " + args.artist_tag
            audio["artist"] = args.artist_tag
        elif args.album_tag is not None:
            audio["title"] = str(i) + " " + args.album_tag
            audio["album"] = args.album_tag
        audio.save()

    def _cp(i, total, entry):
        src, dst = entry
        shutil.copy(src, dst)
        _set_tags(i, total, dst)
        print("{:>4}/{:<4} {}".format(i, total, dst))
        return entry

    copy = (lambda i, x: _cp(fcount - i - 1, fcount - 1, x)) if args.reverse else lambda i, x: _cp(i + 1, fcount - 1, x)

    return [copy(i, x) for i, x in enumerate(belt)]


def retrieve_args():
    parser = argparse.ArgumentParser(description=utility_description)
    parser.add_argument("-t", "--tree-dst", help="retain the tree structure of the source album at destination", action="store_true")
    parser.add_argument("-p", "--drop-dst", help="do not create destination directory", action="store_true")
    parser.add_argument("-r", "--reverse", help="copy files in reverse order (number one file is the last to be copied)", action="store_true")
    parser.add_argument("-u", "--unified-name",
        help="destination root directory name and file names are based on UNIFIED_NAME,serial number prepended, file extentions retained")
    parser.add_argument("-b", "--album-num", help="0..99; prepend ALBUM_NUM to the destination root directory name")
    parser.add_argument("-a", "--artist-tag", help="artist tag name")
    parser.add_argument("-g", "--album-tag", help="album tag name")
    parser.add_argument('src_dir', help="source directory")
    parser.add_argument('dst_dir', help="general destination directory")
    rg = parser.parse_args()
    rg.src_dir = os.path.abspath(rg.src_dir)    # Takes care of the trailing slash, too
    rg.dst_dir = os.path.abspath(rg.dst_dir)
    return rg


def main():
    global args

    warnings.resetwarnings()
    warnings.simplefilter('ignore')

    args = retrieve_args()
    copy_album()


if __name__ == '__main__':
    main()
