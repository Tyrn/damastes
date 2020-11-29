#!/usr/bin/env python
"""
Audio album builder. See description.
"""

import sys

if sys.version_info < (3, 6, 0):
    sys.stderr.write("You need python 3.6 or later to run this script\n")
    sys.exit(1)

from typing import List, Tuple, Iterator, Any
import mutagen as mt
import os
import re
import shutil
import argparse
import warnings
import functools as ft
from pathlib import Path


def has_ext_of(path: Path, ext: str) -> bool:
    """
    Returns True, if path has extension ext, case and leading dot insensitive.
    """
    return path.suffix.lstrip(".").upper() == ext.lstrip(".").upper()


def str_strip_numbers(str_alphanum: str) -> List[int]:
    """
    Returns a vector of integer numbers
    embedded in a string argument.
    """
    return [int(x) for x in re.compile(r"\d+").findall(str_alphanum)]


Ord = int  # LT (negative), EQ (zero) GT (positive).


def strcmp_c(str_x, str_y) -> Ord:
    """
    Compares strings; also lists of integers using 'string semantics'.
    """
    return 0 if str_x == str_y else -1 if str_x < str_y else 1


def strcmp_naturally(str_x: str, str_y: str) -> Ord:
    """
    If both strings contain digits, returns numerical comparison based on the numeric
    values embedded in the strings, otherwise returns the standard string comparison.
    The idea of the natural sort as opposed to the standard lexicographic sort is one of coping
    with the possible absence of the leading zeros in 'numbers' of files or directories.
    """
    num_x = str_strip_numbers(str_x)
    num_y = str_strip_numbers(str_y)
    return (
        strcmp_c(num_x, num_y)
        if num_x != [] and num_y != []
        else strcmp_c(str_x, str_y)
    )


def path_compare(path_x: Path, path_y: Path) -> Ord:
    """
    Compares two paths (directories).
    """
    return (
        strcmp_c(str(path_x), str(path_y))
        if ARGS.sort_lex
        else strcmp_naturally(str(path_x), str(path_y))
    )


def file_compare(path_x: Path, path_y: Path) -> Ord:
    """
    Compares two paths, filenames only, ignoring extensions.
    """
    return (
        strcmp_c(path_x.stem, path_y.stem)
        if ARGS.sort_lex
        else strcmp_naturally(path_x.stem, path_y.stem)
    )


def mutagen_file(name: Path):
    """
    Returns Mutagen thing, if name looks like an audio file path, else returns None.
    """
    file = mt.File(name, easy=True)
    if ARGS.file_type is None:
        return file
    return file if has_ext_of(name, ARGS.file_type) else None


def is_audiofile(name: Path) -> bool:
    """
    Returns True, if name is an audio file, else returns False.
    """
    return name.is_file() and mutagen_file(name)


def list_dir_groom(abs_path: Path, rev=False) -> Tuple[List[Path], List[Path]]:
    """
    Returns a tuple of: (0) naturally sorted list of
    offspring directory paths (1) naturally sorted list
    of offspring file paths.
    """
    lst = [abs_path.joinpath(x) for x in os.listdir(abs_path)]
    dirs = sorted(
        [x for x in lst if x.is_dir()],
        key=ft.cmp_to_key(
            (lambda xp, yp: -path_compare(xp, yp)) if rev else path_compare
        ),
    )
    files = sorted(
        [x for x in lst if is_audiofile(x)],
        key=ft.cmp_to_key(
            (lambda xf, yf: -file_compare(xf, yf)) if rev else file_compare
        ),
    )
    return dirs, files


def decorate_dir_name(i: int, path: Path) -> str:
    """
    Prepends decimal i to path name.
    """
    return ("" if ARGS.strip_decorations else (str(i).zfill(3) + "-")) + path.name


def artist() -> str:
    """
    Generates Artist prefix for a directory/file name.
    """
    return ARGS.artist_tag if ARGS.artist_tag else ""


def decorate_file_name(cntw: int, i: int, dst_step: List[str], path: Path) -> str:
    """
    Prepends zero padded decimal i to path name.
    """
    if ARGS.strip_decorations:
        return path.name
    prefix = str(i).zfill(cntw) + (
        "-" + "-".join(dst_step) + "-"
        if ARGS.prepend_subdir_name and not ARGS.tree_dst and len(dst_step) > 0
        else "-"
    )
    return prefix + (
        ARGS.unified_name + " - " + artist() + path.suffix
        if ARGS.unified_name
        else path.name
    )


def traverse_tree_dst(
    src_dir: Path, dst_root: Path, dst_step: List[str], cntw: int
) -> Iterator[Tuple[Path, Path]]:
    """
    Recursively traverses the source directory and yields a sequence of (src, tree dst) pairs;
    the destination directory and file names get decorated according to options.
    """
    dirs, files = list_dir_groom(src_dir)

    for i, directory in enumerate(dirs):
        step = list(dst_step)
        step.append(decorate_dir_name(i, directory))
        os.mkdir(dst_root.joinpath(*step))
        yield from traverse_tree_dst(directory, dst_root, step, cntw)

    for i, file in enumerate(files):
        dst_path = dst_root.joinpath(*dst_step).joinpath(
            decorate_file_name(cntw, i, dst_step, file)
        )
        yield file, dst_path


def traverse_flat_dst(
    src_dir: Path, dst_root: Path, fcount: List[int], dst_step: List[str], cntw: int
) -> Iterator[Tuple[Path, Path]]:
    """
    Recursively traverses the source directory and yields a sequence of (src, flat dst) pairs;
    the destination directory and file names get decorated according to options.
    """
    dirs, files = list_dir_groom(src_dir)

    for directory in dirs:
        step = list(dst_step)
        step.append(directory.name)
        yield from traverse_flat_dst(directory, dst_root, fcount, step, cntw)

    for file in files:
        dst_path = dst_root.joinpath(
            decorate_file_name(cntw, fcount[0], dst_step, file)
        )
        fcount[0] += 1
        yield file, dst_path


def traverse_flat_dst_r(
    src_dir: Path, dst_root: Path, fcount: List[int], dst_step: List[str], cntw: int
) -> Iterator[Tuple[Path, Path]]:
    """
    Recursively traverses the source directory backwards (-r) and yields a sequence
    of (src, flat dst) pairs;
    the destination directory and file names get decorated according to options.
    """
    dirs, files = list_dir_groom(src_dir, rev=True)

    for file in files:
        dst_path = dst_root.joinpath(
            decorate_file_name(cntw, fcount[0], dst_step, file)
        )
        fcount[0] -= 1
        yield file, dst_path

    for directory in dirs:
        step = list(dst_step)
        step.append(directory.name)
        yield from traverse_flat_dst_r(directory, dst_root, fcount, step, cntw)


def groom(src: Path, dst: Path, cnt: int) -> Iterator[Tuple[Path, Path]]:
    """
    Makes an 'executive' run of traversing the source directory; returns the 'ammo belt' generator.
    """
    cntw = len(str(cnt))  # File number substring need not be wider than this

    if ARGS.tree_dst:
        return traverse_tree_dst(src, dst, [], cntw)
    if ARGS.reverse:
        return traverse_flat_dst_r(src, dst, [cnt], [], cntw)
    return traverse_flat_dst(src, dst, [1], [], cntw)


def build_album() -> Tuple[int, Iterator[Tuple[Path, Path]]]:
    """
    Sets up boilerplate required by the options and returns the ammo belt generator
    of (src, dst) pairs.
    """
    prefix = (str(ARGS.album_num).zfill(2) + "-") if ARGS.album_num else ""
    base_dst = prefix + (
        artist() + " - " + ARGS.unified_name if ARGS.unified_name else ARGS.src_dir.name
    )

    executive_dst = ARGS.dst_dir.joinpath("" if ARGS.drop_dst else base_dst)

    def audiofiles_count(directory: Path) -> int:
        """
        Returns full recursive count of audiofiles in directory.
        """
        cnt = 0

        for root, _dirs, files in os.walk(directory):
            for name in files:
                if is_audiofile(Path(root).joinpath(name)):
                    cnt += 1
        return cnt

    tot = audiofiles_count(ARGS.src_dir)

    if tot < 1:
        print(
            f'There are no supported audio files in the source directory "{ARGS.src_dir}".'
        )
        sys.exit()

    if not ARGS.drop_dst:
        if executive_dst.exists():
            print(f'Destination directory "{executive_dst}" already exists.')
            sys.exit()
        else:
            os.mkdir(executive_dst)

    return tot, groom(ARGS.src_dir, executive_dst, tot)


def make_initials(authors: str, sep=".", trail=".", hyph="-") -> str:
    """
    Reduces authors to initials.
    """
    by_space = lambda s: sep.join(
        x[0] for x in re.split(rf"[\s{sep}]+", s) if x
    ).upper()
    by_hyph = (
        lambda s: hyph.join(by_space(x) for x in re.split(rf"\s*(?:{hyph}\s*)+", s))
        + trail
    )

    sans_monikers = re.sub(r"\"(?:\\.|[^\"\\])*\"", " ", authors)

    return ",".join(by_hyph(author) for author in sans_monikers.split(","))


def copy_album() -> None:
    """
    Runs through the ammo belt and does copying, in the reverse order if necessary.
    """

    def set_tags(i: int, total: int, source: Path, path: Path) -> None:
        def make_title(tagging: str) -> str:
            if ARGS.file_title_num:
                return str(i) + ">" + source.stem
            if ARGS.file_title:
                return source.stem
            return str(i) + " " + tagging

        audio = mutagen_file(path)
        if audio is None:
            return

        if not ARGS.drop_tracknumber:
            audio["tracknumber"] = str(i) + "/" + str(total)
        if ARGS.artist_tag and ARGS.album_tag:
            audio["title"] = make_title(
                make_initials(ARGS.artist_tag) + " - " + ARGS.album_tag
            )
            audio["artist"] = ARGS.artist_tag
            audio["album"] = ARGS.album_tag
        elif ARGS.artist_tag:
            audio["title"] = make_title(ARGS.artist_tag)
            audio["artist"] = ARGS.artist_tag
        elif ARGS.album_tag:
            audio["title"] = make_title(ARGS.album_tag)
            audio["album"] = ARGS.album_tag
        audio.save()

    def copy_file(i: int, total: int, entry: Tuple[Path, Path]) -> None:
        src, dst = entry
        shutil.copy(src, dst)
        set_tags(i, total, src, dst)
        if ARGS.verbose:
            print(f"{i:>4}/{total:<4} {dst}")
        else:
            sys.stdout.write(".")
            sys.stdout.flush()

    tot, belt = build_album()

    if not ARGS.verbose:
        sys.stdout.write("Starting ")

    if ARGS.reverse:
        for i, entry in enumerate(belt):
            copy_file(tot - i, tot, entry)
    else:
        for i, entry in enumerate(belt):
            copy_file(i + 1, tot, entry)

    if not ARGS.verbose:
        print(f" Done ({tot}).")


def retrieve_args() -> Any:
    """
    Parses the command line and returns a collection of arguments.
    """
    parser = argparse.ArgumentParser(
        description="""
    pcp "Procrustes" SmArT is a CLI utility for copying subtrees containing supported audio
    files in sequence, naturally sorted.
    The end result is a "flattened" copy of the source subtree. "Flattened" means
    that only a namesake of the root source directory is created, where all the files get
    copied to, names prefixed with a serial number. Tag "Track Number"
    is set, tags "Title", "Artist", and "Album" can be replaced optionally.
    The writing process is strictly sequential: either starting with the number one file,
    or in the reversed order. This can be important for some mobile devices.
    """
    )

    parser.add_argument("-v", "--verbose", help="verbose output", action="store_true")
    parser.add_argument(
        "-d", "--drop-tracknumber", help="do not set track numbers", action="store_true"
    )
    parser.add_argument(
        "-s",
        "--strip-decorations",
        help="strip file and directory name decorations",
        action="store_true",
    )
    parser.add_argument(
        "-f", "--file-title", help="use file name for title tag", action="store_true"
    )
    parser.add_argument(
        "-F",
        "--file-title-num",
        help="use numbered file name for title tag",
        action="store_true",
    )
    parser.add_argument(
        "-x", "--sort-lex", help="sort files lexicographically", action="store_true"
    )
    parser.add_argument(
        "-t",
        "--tree-dst",
        help="retain the tree structure of the source album at destination",
        action="store_true",
    )
    parser.add_argument(
        "-p",
        "--drop-dst",
        help="do not create destination directory",
        action="store_true",
    )
    parser.add_argument(
        "-r",
        "--reverse",
        help="copy files in reverse order (number one file is the last to be copied)",
        action="store_true",
    )
    parser.add_argument(
        "-e", "--file-type", help="accept only audio files of the specified type"
    )
    parser.add_argument(
        "-i",
        "--prepend-subdir-name",
        help="prepend current subdirectory name to a file name",
        action="store_true",
    )
    parser.add_argument(
        "-u",
        "--unified-name",
        help="""
                        destination root directory name and file names are based on UNIFIED_NAME,
                        serial number prepended, file extensions retained; also album tag,
                        if the latter is not specified explicitly
                        """,
    )
    parser.add_argument(
        "-b",
        "--album-num",
        help="0..99; prepend ALBUM_NUM to the destination root directory name",
    )
    parser.add_argument("-a", "--artist-tag", help="artist tag name")
    parser.add_argument("-g", "--album-tag", help="album tag name")
    parser.add_argument("src_dir", help="source directory")
    parser.add_argument("dst_dir", help="general destination directory")
    args = parser.parse_args()
    args.src_dir = Path(
        args.src_dir
    ).absolute()  # Takes care of the trailing slash, too.
    args.dst_dir = Path(args.dst_dir).absolute()

    if not args.src_dir.is_dir():
        print(f'Source directory "{args.src_dir}" is not there.')
        sys.exit()
    if not args.dst_dir.is_dir():
        print(f'Destination path "{args.dst_dir}" is not there.')
        sys.exit()

    if args.tree_dst and args.reverse:
        print("  *** -t option ignored (conflicts with -r) ***")
        args.tree_dst = False

    if args.unified_name and args.album_tag is None:
        args.album_tag = args.unified_name

    return args


ARGS: Any = None


def main() -> None:
    """
    Entry point.
    """
    global ARGS

    try:
        warnings.resetwarnings()
        warnings.simplefilter("ignore")

        ARGS = retrieve_args()
        copy_album()
    except KeyboardInterrupt as ctrl_c:
        sys.exit(ctrl_c)


if __name__ == "__main__":
    main()
