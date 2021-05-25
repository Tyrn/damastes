#!/usr/bin/env python
"""
Audio album builder. See description.
"""

import sys

if sys.version_info < (3, 6, 0):
    sys.stderr.write("You need python 3.6 or later to run this script\n")
    sys.exit(1)

from py_procr import __version__
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

    >>> has_ext_of(Path("bra.vo/charlie.ogg"), "OGG")
    True
    >>> has_ext_of(Path("bra.vo/charlie.ogg"), "mp3")
    False
    """
    return path.suffix.lstrip(".").upper() == ext.lstrip(".").upper()


def str_strip_numbers(str_alphanum: str) -> List[int]:
    """
    Returns a vector of integer numbers
    embedded in a string argument.

    >>> str_strip_numbers("ab11cdd2k.144")
    [11, 2, 144]
    """
    return [int(x) for x in re.compile(r"\d+").findall(str_alphanum)]


Ord = int  # LT (negative), EQ (zero) GT (positive).


def strcmp_c(str_x, str_y) -> Ord:
    """
    Compares strings; also lists of integers using 'string semantics'.

    >>> strcmp_c("aardvark", "bobo")
    -1
    >>> strcmp_c([1, 4], [1, 4, 16])
    -1
    >>> strcmp_c([2, 8], [2, 2, 3])
    1
    >>> strcmp_c([11, 2], [0xb, 2])
    0
    """
    return 0 if str_x == str_y else -1 if str_x < str_y else 1


def strcmp_naturally(str_x: str, str_y: str) -> Ord:
    """
    If both strings contain digits, returns numerical comparison based on the numeric
    values embedded in the strings, otherwise returns the standard string comparison.
    The idea of the natural sort as opposed to the standard lexicographic sort is one of coping
    with the possible absence of the leading zeros in 'numbers' of files or directories.

    >>> strcmp_naturally("2charlie", "10alfa")
    -1
    >>> strcmp_naturally("charlie", "zulu")
    -1
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
    offspring directory names (1) naturally sorted list
    of offspring file names.
    """
    lst = os.listdir(abs_path)
    dirs = sorted(
        [Path(x) for x in lst if abs_path.joinpath(x).is_dir()],
        key=ft.cmp_to_key(
            (lambda xp, yp: -path_compare(xp, yp)) if rev else path_compare
        ),
    )
    files = sorted(
        [Path(x) for x in lst if is_audiofile(abs_path.joinpath(x))],
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


def decorate_file_name(i: int, dst_step: List[str], path: Path) -> str:
    """
    Prepends zero padded decimal i to path name.
    """
    if ARGS.strip_decorations:
        return path.name
    prefix = str(i).zfill(len(str(FILES_TOTAL))) + (
        "-" + "-".join(dst_step) + "-"
        if ARGS.prepend_subdir_name and not ARGS.tree_dst and len(dst_step) > 0
        else "-"
    )
    return prefix + (
        ARGS.unified_name + " - " + artist() + path.suffix
        if ARGS.unified_name
        else path.name
    )


def walk_file_tree(
    src_dir: Path, dst_root: Path, fcount: List[int], dst_step: List[str]
) -> Iterator[Tuple[int, Path, Path, str]]:
    """
    Recursively traverses the source directory and yields a tuple of copying attributes;
    the destination directory and file names get decorated according to options.
    """
    dirs, files = list_dir_groom(src_dir, ARGS.reverse)

    def dir_flat(dirs):
        for directory in dirs:
            step = list(dst_step)
            step.append(directory.name)
            yield from walk_file_tree(
                src_dir.joinpath(directory), dst_root, fcount, step
            )

    def file_flat(files):
        for file in files:
            yield fcount[0], src_dir.joinpath(file), dst_root, decorate_file_name(
                fcount[0], dst_step, file
            )
            fcount[0] += -1 if ARGS.reverse else 1

    def reverse(i, lst):
        return len(lst) - i if ARGS.reverse else i + 1

    def dir_tree(dirs):
        for i, directory in enumerate(dirs):
            step = list(dst_step)
            step.append(decorate_dir_name(reverse(i, dirs), directory))
            yield from walk_file_tree(
                src_dir.joinpath(directory), dst_root, fcount, step
            )

    def file_tree(files):
        for i, file in enumerate(files):
            yield fcount[0], src_dir.joinpath(file), dst_root.joinpath(
                *dst_step
            ), decorate_file_name(reverse(i, files), dst_step, file)
            fcount[0] += -1 if ARGS.reverse else 1

    dir_fund, file_fund = (
        (dir_tree, file_tree) if ARGS.tree_dst else (dir_flat, file_flat)
    )

    if ARGS.reverse:
        yield from file_fund(files)
        yield from dir_fund(dirs)
    else:
        yield from dir_fund(dirs)
        yield from file_fund(files)


def album() -> Iterator[Tuple[int, Path, Path, str]]:
    """
    Sets up boilerplate required by the options and returns the ammo belt generator
    of (src, dst) pairs.
    """
    global FILES_TOTAL

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

    FILES_TOTAL = audiofiles_count(ARGS.src_dir)

    if FILES_TOTAL < 1:
        print(
            f'There are no supported audio files in the source directory "{ARGS.src_dir}".'
        )
        sys.exit()

    if not ARGS.drop_dst and not ARGS.dry_run:
        if executive_dst.exists():
            if ARGS.overwrite:
                try:
                    shutil.rmtree(executive_dst)
                except FileNotFoundError:
                    print(f'Failed to remove "{executive_dst}".')
                    sys.exit()
            else:
                print(f'Destination directory "{executive_dst}" already exists.')
                sys.exit()
        executive_dst.mkdir()

    return walk_file_tree(
        ARGS.src_dir, executive_dst, [FILES_TOTAL if ARGS.reverse else 1], []
    )


def make_initials(authors: str, sep=".", trail=".", hyph="-") -> str:
    """
    Reduces authors to initials.

    >>> make_initials('Ignacio "Castigador" Vazquez-Abrams, Estefania Cassingena Navone')
    'I.V-A.,E.C.N.'
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

    def set_tags(i: int, source: Path, path: Path) -> None:
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
            audio["tracknumber"] = str(i) + "/" + str(FILES_TOTAL)
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

    def copy_file(entry: Tuple[int, Path, Path, str]) -> None:
        i, src, dst_path, target_file_name = entry
        dst = dst_path.joinpath(target_file_name)
        if not ARGS.dry_run:
            dst_path.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
            set_tags(i, src, dst)
        if ARGS.verbose:
            print(f"{i:>4}/{FILES_TOTAL} \U0001f3a7 {dst}")
        else:
            sys.stdout.write(".")
            sys.stdout.flush()

    if not ARGS.verbose:
        sys.stdout.write("Starting ")

    for entry in album():
        copy_file(entry)

    if not ARGS.verbose:
        print(f" Done ({FILES_TOTAL}).")


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

    parser.add_argument(
        "-V",
        "--version",
        help="package version",
        action="version",
        version=f"%(prog)s (version {__version__})",
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
        "-w",
        "--overwrite",
        help="silently remove existing destination directory (not recommended)",
        action="store_true",
    )
    parser.add_argument(
        "-y",
        "--dry-run",
        help="without actually copying the files",
        action="store_true",
    )
    parser.add_argument(
        "-i",
        "--prepend-subdir-name",
        help="prepend current subdirectory name to a file name",
        action="store_true",
    )
    parser.add_argument(
        "-e", "--file-type", help="accept only audio files of the specified type"
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

    if args.unified_name and args.album_tag is None:
        args.album_tag = args.unified_name

    return args


ARGS: Any = None
FILES_TOTAL = -1


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
