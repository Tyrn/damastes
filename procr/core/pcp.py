#!/usr/bin/env python

import sys

if sys.version_info < (3, 6, 0):
    sys.stderr.write("You need python 3.6 or later to run this script\n")
    sys.exit(1)

import mutagen as mt
import os
import re
import shutil
import argparse
import warnings
import functools as ft
from pathlib import Path


def has_ext_of(path, ext):
    """
    Returns True, if path has extension ext, case and leading dot insensitive.
    """
    return path.suffix.lstrip(".").upper() == ext.lstrip(".").upper()


def str_strip_numbers(s):
    """
    Returns a vector of integer numbers
    embedded in a string argument.
    """
    return [int(x) for x in re.compile('\d+').findall(s)]


def cmpstr_c(x, y):
    """
    Compares strings; also lists of integers using 'string semantics'.
    """
    return 0 if x == y else -1 if x < y else 1


def cmpstr_naturally(str_x, str_y):
    """
    If both strings contain digits, returns numerical comparison based on the numeric
    values embedded in the strings, otherwise returns the standard string comparison.
    The idea of the natural sort as opposed to the standard lexicographic sort is one of coping
    with the possible absence of the leading zeros in 'numbers' of files or directories.
    """
    num_x = str_strip_numbers(str_x)
    num_y = str_strip_numbers(str_y)
    return cmpstr_c(num_x, num_y) if num_x != [] and num_y != [] else cmpstr_c(
        str_x, str_y)


def compare_path(x, y):
    """
    Compares two paths (directories).
    """
    return cmpstr_c(str(x), str(y)) if args.sort_lex else cmpstr_naturally(
        str(x), str(y))


def compare_file(x, y):
    """
    Compares two paths, filenames only, ignoring extensions.
    """
    return cmpstr_c(x.stem, y.stem) if args.sort_lex else cmpstr_naturally(
        x.stem, y.stem)


args = None


def mutagen_file(x):
    """
    Returns Mutagen thing, if x looks like an audio file path, else returns None.
    """
    global args

    f = mt.File(x, easy=True)
    if args.file_type is None:
        return f
    return f if has_ext_of(x, args.file_type) else None


def isaudiofile(x):
    """
    Returns True, if x is an audio file, else returns False.
    """
    return x.is_file() and mutagen_file(x)


def list_dir_groom(abs_path, rev=False):
    """
    Returns a tuple of: (0) naturally sorted list of
    offspring directory paths (1) naturally sorted list
    of offspring file paths.
    """
    lst = [abs_path.joinpath(x) for x in os.listdir(abs_path)]
    dirs = sorted(
        [x for x in lst if x.is_dir()],
        key=ft.cmp_to_key((
            lambda xp, yp: -compare_path(xp, yp)) if rev else compare_path))
    files = sorted(
        [x for x in lst if isaudiofile(x)],
        key=ft.cmp_to_key((
            lambda xf, yf: -compare_file(xf, yf)) if rev else compare_file))
    return dirs, files


def decorate_dir_name(i, path):
    return ("" if args.strip_decorations else
            (str(i).zfill(3) + "-")) + path.name


def artist():
    """
    Generates Artist prefix for directory/file name.
    """
    global args

    return args.artist_tag if args.artist_tag else ""


def decorate_file_name(cntw, i, dst_step, path):
    global args

    if args.strip_decorations: return path.name
    prefix = (str(i).zfill(cntw) +
              ('-' + '-'.join(dst_step) + '-' if args.prepend_subdir_name
               and not args.tree_dst and len(dst_step) else '-'))
    return prefix + (args.unified_name + " - " + artist() + path.suffix
                     if args.unified_name else path.name)


def traverse_tree_dst(src_dir, dst_root, dst_step, cntw):
    """
    Recursively traverses the source directory and yields a sequence of (src, tree dst) pairs;
    the destination directory and file names get decorated according to options.
    """
    dirs, files = list_dir_groom(src_dir)

    for i, d in enumerate(dirs):
        step = list(dst_step)
        step.append(decorate_dir_name(i, d))
        os.mkdir(dst_root.joinpath(*step))
        yield from traverse_tree_dst(d, dst_root, step, cntw)

    for i, f in enumerate(files):
        dst_path = dst_root.joinpath(*dst_step).joinpath(
            decorate_file_name(cntw, i, dst_step, f))
        yield f, dst_path


def traverse_flat_dst(src_dir, dst_root, fcount, dst_step, cntw):
    """
    Recursively traverses the source directory and yields a sequence of (src, flat dst) pairs;
    the destination directory and file names get decorated according to options.
    """
    dirs, files = list_dir_groom(src_dir)

    for d in dirs:
        step = list(dst_step)
        step.append(d.name)
        yield from traverse_flat_dst(d, dst_root, fcount, step, cntw)

    for f in files:
        dst_path = dst_root.joinpath(
            decorate_file_name(cntw, fcount[0], dst_step, f))
        fcount[0] += 1
        yield f, dst_path


def traverse_flat_dst_r(src_dir, dst_root, fcount, dst_step, cntw):
    """
    Recursively traverses the source directory backwards (-r) and yields a sequence of (src, flat dst) pairs;
    the destination directory and file names get decorated according to options.
    """
    dirs, files = list_dir_groom(src_dir, rev=True)

    for f in files:
        dst_path = dst_root.joinpath(
            decorate_file_name(cntw, fcount[0], dst_step, f))
        fcount[0] -= 1
        yield f, dst_path

    for d in dirs:
        step = list(dst_step)
        step.append(d.name)
        yield from traverse_flat_dst_r(d, dst_root, fcount, step, cntw)


def groom(src, dst, cnt):
    """
    Makes an 'executive' run of traversing the source directory; returns the 'ammo belt' generator.
    """
    global args
    cntw = len(str(cnt))  # File number substring need not be wider than this

    if args.tree_dst:
        return traverse_tree_dst(src, dst, [], cntw)
    else:
        if args.reverse:
            return traverse_flat_dst_r(src, dst, [cnt], [], cntw)
        else:
            return traverse_flat_dst(src, dst, [1], [], cntw)


def build_album():
    """
    Sets up boilerplate required by the options and returns the ammo belt generator
    of (src, dst) pairs.
    """
    global args

    prefix = (str(args.album_num).zfill(2) + "-") if args.album_num else ""
    base_dst = prefix + (artist() + " - " + args.unified_name
                         if args.unified_name else args.src_dir.name)

    executive_dst = args.dst_dir.joinpath("" if args.drop_dst else base_dst)

    def audiofiles_count(directory):
        """
        Returns full recursive count of audiofiles in directory.
        """
        cnt = 0

        for root, dirs, files in os.walk(directory):
            for name in files:
                if isaudiofile(Path(root).joinpath(name)):
                    cnt += 1
        return cnt

    tot = audiofiles_count(args.src_dir)

    if tot < 1:
        print(
            f'There are no supported audio files in the source directory "{args.src_dir}".'
        )
        sys.exit()

    if not args.drop_dst:
        if executive_dst.exists():
            print(f'Destination directory "{executive_dst}" already exists.')
            sys.exit()
        else:
            os.mkdir(executive_dst)

    return tot, groom(args.src_dir, executive_dst, tot)


def make_initials(authors, sep=".", trail=".", hyph="-"):
    """
    Reduces authors to initials.
    """
    by_space = lambda s: sep.join(x[0] for x in re.split(f"[\s{sep}]+", s) if x
                                  ).upper()
    by_hyph = lambda s: hyph.join(
        by_space(x) for x in re.split(f"\s*(?:{hyph}\s*)+", s)) + trail

    sans_monikers = re.sub(r"\"(?:\\.|[^\"\\])*\"", " ", authors)

    return ','.join(by_hyph(author) for author in sans_monikers.split(','))


def copy_album():
    """
    Runs through the ammo belt and does copying, in the reverse order if necessary.
    """
    global args

    def _set_tags(i, total, source, path):
        def _title(s):
            if args.file_title_num:
                return str(i) + '>' + source.stem
            if args.file_title:
                return source.stem
            return str(i) + " " + s

        audio = mutagen_file(path)
        if audio is None:
            return

        if not args.drop_tracknumber:
            audio["tracknumber"] = str(i) + "/" + str(total)
        if args.artist_tag and args.album_tag:
            audio["title"] = _title(
                make_initials(args.artist_tag) + " - " + args.album_tag)
            audio["artist"] = args.artist_tag
            audio["album"] = args.album_tag
        elif args.artist_tag:
            audio["title"] = _title(args.artist_tag)
            audio["artist"] = args.artist_tag
        elif args.album_tag:
            audio["title"] = _title(args.album_tag)
            audio["album"] = args.album_tag
        audio.save()

    def _cp(i, total, entry):
        src, dst = entry
        shutil.copy(src, dst)
        _set_tags(i, total, src, dst)
        if args.verbose:
            print(f"{i:>4}/{total:<4} {dst}")
        else:
            sys.stdout.write('.')
            sys.stdout.flush()

    tot, belt = build_album()

    if not args.verbose: sys.stdout.write('Starting ')

    if args.reverse:
        for i, x in enumerate(belt):
            _cp(tot - i, tot, x)
    else:
        for i, x in enumerate(belt):
            _cp(i + 1, tot, x)

    if not args.verbose: print(f' Done ({tot}).')


def retrieve_args():
    parser = argparse.ArgumentParser(description='''
    pcp "Procrustes" SmArT is a CLI utility for copying subtrees containing supported audio
    files in sequence, naturally sorted.
    The end result is a "flattened" copy of the source subtree. "Flattened" means
    that only a namesake of the root source directory is created, where all the files get
    copied to, names prefixed with a serial number. Tag "Track Number"
    is set, tags "Title", "Artist", and "Album" can be replaced optionally.
    The writing process is strictly sequential: either starting with the number one file,
    or in the reversed order. This can be important for some mobile devices.
    ''')

    parser.add_argument(
        "-v", "--verbose", help="verbose output", action="store_true")
    parser.add_argument(
        "-d",
        "--drop-tracknumber",
        help="do not set track numbers",
        action="store_true")
    parser.add_argument(
        "-s",
        "--strip-decorations",
        help="strip file and directory name decorations",
        action="store_true")
    parser.add_argument(
        "-f",
        "--file-title",
        help="use file name for title tag",
        action="store_true")
    parser.add_argument(
        "-F",
        "--file-title-num",
        help="use numbered file name for title tag",
        action="store_true")
    parser.add_argument(
        "-x",
        "--sort-lex",
        help="sort files lexicographically",
        action="store_true")
    parser.add_argument(
        "-t",
        "--tree-dst",
        help="retain the tree structure of the source album at destination",
        action="store_true")
    parser.add_argument(
        "-p",
        "--drop-dst",
        help="do not create destination directory",
        action="store_true")
    parser.add_argument(
        "-r",
        "--reverse",
        help=
        "copy files in reverse order (number one file is the last to be copied)",
        action="store_true")
    parser.add_argument(
        "-e",
        "--file-type",
        help="accept only audio files of the specified type")
    parser.add_argument(
        "-i",
        "--prepend-subdir-name",
        help="prepend current subdirectory name to a file name",
        action="store_true")
    parser.add_argument(
        "-u",
        "--unified-name",
        help='''
                        destination root directory name and file names are based on UNIFIED_NAME,
                        serial number prepended, file extensions retained; also album tag,
                        if the latter is not specified explicitly
                        ''')
    parser.add_argument(
        "-b",
        "--album-num",
        help="0..99; prepend ALBUM_NUM to the destination root directory name")
    parser.add_argument("-a", "--artist-tag", help="artist tag name")
    parser.add_argument("-g", "--album-tag", help="album tag name")
    parser.add_argument('src_dir', help="source directory")
    parser.add_argument('dst_dir', help="general destination directory")
    rg = parser.parse_args()
    rg.src_dir = Path(
        rg.src_dir).absolute()  # Takes care of the trailing slash, too.
    rg.dst_dir = Path(rg.dst_dir).absolute()

    if not rg.src_dir.is_dir():
        print(f'Source directory "{rg.src_dir}" is not there.')
        sys.exit()
    if not rg.dst_dir.is_dir():
        print(f'Destination path "{rg.dst_dir}" is not there.')
        sys.exit()

    if rg.tree_dst and rg.reverse:
        print("  *** -t option ignored (conflicts with -r) ***")
        rg.tree_dst = False

    if rg.unified_name and rg.album_tag is None:
        rg.album_tag = rg.unified_name

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
