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
from yaspin import yaspin
from math import log
from pathlib import Path
from tempfile import mkstemp


def has_ext_of(path: Path, *extensions: str) -> bool:
    """
    Returns True, if path has an extension from extensions,
    case and leading dot insensitive.

    >>> has_ext_of(Path("bra.vo/charlie.ogg"), "OGG")
    True
    >>> has_ext_of(Path("bra.vo/charlie.ogg"), "mp3")
    False
    >>> has_ext_of(Path("bra.vo/charlie.ogg"), "mp3", "mp4", "flac")
    False
    >>> has_ext_of(Path("bra.vo/charlie.ogg"), *["mp3", "mp4", "flac"])
    False
    """
    path_ext = path.suffix.lstrip(".").upper()
    for ext in extensions:
        if path_ext == ext.lstrip(".").upper():
            return True
    return False


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


def mutagen_file(name: Path, spinner=None):
    """
    Returns Mutagen thing, if name looks like an audio file path, else returns None.
    """
    global INVALID_TOTAL, SUSPICIOUS_TOTAL

    if ARGS.file_type and not has_ext_of(name, ARGS.file_type):
        return None

    name_to_print: str = str(name) if ARGS.verbose else name.name

    try:
        file = mt.File(name, easy=True)
    except mt.MutagenError as mt_error:
        if spinner:
            spinner.write(f" {INVALID_ICON} >>{mt_error}>> {name_to_print}")
            INVALID_TOTAL += 1
        return None

    if spinner and file is None and has_ext_of(name, *KNOWN_EXTENSIONS):
        spinner.write(f" {SUSPICIOUS_ICON} {name_to_print}")
        SUSPICIOUS_TOTAL += 1
    return file


def is_audiofile(name: Path, spinner=None) -> bool:
    """
    Returns True, if name is an audio file, else returns False.
    """
    if name.is_file():
        file = mutagen_file(name, spinner)
        if file is not None:
            return True
    return False


def list_dir_groom(abs_path: Path, rev=False) -> Tuple[List[Path], List[Path]]:
    """
    Returns a tuple of: (0) naturally sorted list of
    offspring directory names (1) naturally sorted list
    of offspring file names.
    """
    lst = os.listdir(abs_path)
    dirs = sorted(
        [Path(x) for x in lst if (abs_path / x).is_dir()],
        key=ft.cmp_to_key(
            (lambda xp, yp: -path_compare(xp, yp)) if rev else path_compare
        ),
    )
    files = sorted(
        [Path(x) for x in lst if is_audiofile(abs_path / x)],
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
            yield from walk_file_tree(src_dir / directory, dst_root, fcount, step)

    def file_flat(files):
        for file in files:
            yield fcount[0], src_dir / file, dst_root, decorate_file_name(
                fcount[0], dst_step, file
            )
            fcount[0] += -1 if ARGS.reverse else 1

    def reverse(i, lst):
        return len(lst) - i if ARGS.reverse else i + 1

    def dir_tree(dirs):
        for i, directory in enumerate(dirs):
            step = list(dst_step)
            step.append(decorate_dir_name(reverse(i, dirs), directory))
            yield from walk_file_tree(src_dir / directory, dst_root, fcount, step)

    def file_tree(files):
        for i, file in enumerate(files):
            yield fcount[0], src_dir / file, dst_root.joinpath(
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


def audiofiles_count(directory: Path, spinner) -> Tuple[int, int]:
    """
    Returns full recursive count of audiofiles in directory.
    """
    cnt, size = 0, 0

    for root, _dirs, files in os.walk(directory):
        for name in files:
            abs_path = Path(root) / name
            if is_audiofile(abs_path, spinner):
                if cnt % 10 == 0:
                    spinner.text = name
                cnt += 1
                size += abs_path.stat().st_size
    return cnt, size


def album() -> Iterator[Tuple[int, Path, Path, str]]:
    """
    Sets up boilerplate required by the options and returns the ammo belt generator
    of (src, dst) pairs.
    """
    prefix = (str(ARGS.album_num).zfill(2) + "-") if ARGS.album_num else ""
    base_dst = prefix + (
        artist() + " - " + ARGS.unified_name if ARGS.unified_name else ARGS.src_dir.name
    )

    executive_dst = ARGS.dst_dir / ("" if ARGS.drop_dst else base_dst)

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


def human_rough(bytes: int, units=["", "kB", "MB", "GB", "TB", "PB", "EB"]) -> str:
    """
    Returns a human readable string representation of bytes, roughly rounded.

    >>> human_rough(42)
    '42'
    >>> human_rough(1800)
    '1kB'
    >>> human_rough(123456789)
    '117MB'
    """
    return (
        str(bytes) + units[0] if bytes < 1024 else human_rough(bytes >> 10, units[1:])
    )


def human_fine(bytes: int) -> str:
    """
    Returns a human readable string representation of bytes, nicely rounded.

    >>> human_fine(0)
    '0'
    >>> human_fine(1)
    '1'
    >>> human_fine(42)
    '42'
    >>> human_fine(1800)
    '2kB'
    >>> human_fine(123456789)
    '117.7MB'
    >>> human_fine(123456789123)
    '114.98GB'
    """
    unit_list = [("", 0), ("kB", 0), ("MB", 1), ("GB", 2), ("TB", 2), ("PB", 2)]

    if bytes > 1:
        exponent = min(int(log(bytes, 1024)), len(unit_list) - 1)
        quotient = float(bytes) / 1024 ** exponent
        unit, num_decimals = unit_list[exponent]
        return f"{{:.{num_decimals}f}}{{}}".format(quotient, unit)
    if bytes == 0:
        return "0"
    if bytes == 1:
        return "1"
    return f"human_fine error; bytes: {bytes}"


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

    def copy_and_set(index: int, src: Path, dst: Path) -> None:
        shutil.copy(src, dst)
        set_tags(index, src, dst)

    def copy_and_set_via_tmp(index: int, src: Path, dst: Path) -> None:
        fd, path = mkstemp(suffix=src.suffix)
        tmp = Path(path)
        os.close(fd)
        shutil.copy(src, tmp)
        set_tags(index, src, tmp)
        shutil.copy(tmp, dst)
        os.remove(tmp)

    def copy_file(entry: Tuple[int, Path, Path, str]) -> Tuple[int, int]:
        i, src, dst_path, target_file_name = entry
        dst = dst_path / target_file_name
        src_bytes, dst_bytes = src.stat().st_size, 0
        if not ARGS.dry_run:
            dst_path.mkdir(parents=True, exist_ok=True)
            copy_and_set_via_tmp(i, src, dst)
            dst_bytes = dst.stat().st_size
        if ARGS.verbose:
            print(f"{i:>4}/{FILES_TOTAL} {COLUMN_ICON} {dst}", end="")
            if dst_bytes != src_bytes:
                if dst_bytes == 0:
                    print(f"  {COLUMN_ICON} {human_fine(src_bytes)}", end="")
                else:
                    print(f"  {COLUMN_ICON} {(dst_bytes - src_bytes):+d}", end="")
            print("")
        else:
            sys.stdout.write(".")
            sys.stdout.flush()
        return src_bytes, dst_bytes

    if not ARGS.verbose:
        sys.stdout.write("Starting ")

    src_total, dst_total, files_total = 0, 0, 0

    for entry in album():
        src_bytes, dst_bytes = copy_file(entry)
        src_total += src_bytes
        dst_total += dst_bytes
        files_total += 1

    print(f" {DONE_ICON} Done ({FILES_TOTAL}, {human_fine(dst_total)}", end="")
    if ARGS.dry_run:
        print(f"; Volume: {human_fine(src_total)}", end="")
    print(").")
    if files_total != FILES_TOTAL:
        print(f"Fatal error. files_total: {files_total}, FILES_TOTAL: {FILES_TOTAL}")


def retrieve_args() -> Any:
    """
    Parses the command line and returns a collection of arguments.
    """
    parser = argparse.ArgumentParser(
        description=f"""
    pcp "Procrustes" SmArT is a CLI utility for copying subtrees containing supported audio
    files in sequence, naturally sorted.
    The end result is a "flattened" copy of the source subtree. "Flattened" means
    that only a namesake of the root source directory is created, where all the files get
    copied to, names prefixed with a serial number. Tag "Track Number"
    is set, tags "Title", "Artist", and "Album" can be replaced optionally.
    The writing process is strictly sequential: either starting with the number one file,
    or in the reversed order. This can be important for some mobile devices.
    {INVALID_ICON} Broken media;
    {SUSPICIOUS_ICON} Suspicious media;
    {NB} Really useful options.{NB}
    """
    )

    parser.add_argument(
        "-V",
        "--version",
        help="package version",
        action="version",
        version=f"%(prog)s (version {__version__})",
    )
    parser.add_argument(
        "-v", "--verbose", help=f"{NB} verbose output {NB}", action="store_true"
    )
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
        "-c",
        "--count",
        help="just count the files",
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
        help=f"""
                        {NB} destination root directory name and file names are based on UNIFIED_NAME,
                        serial number prepended, file extensions retained; also album tag,
                        if the latter is not specified explicitly {NB}
                        """,
    )
    parser.add_argument(
        "-b",
        "--album-num",
        help="0..99; prepend ALBUM_NUM to the destination root directory name",
    )
    parser.add_argument("-a", "--artist-tag", help=f"{NB} artist tag name {NB}")
    parser.add_argument("-g", "--album-tag", help=f"{NB} album tag name {NB}")
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


NB = "\U0001f53b"
INVALID_ICON = "\U0000274c"
SUSPICIOUS_ICON = "\U00002754"
DONE_ICON = "\U0001f7e2"
COLUMN_ICON = "\U00002714"
KNOWN_EXTENSIONS = ["MP3", "OGG", "M4A", "M4B", "FLAC", "APE"]

ARGS: Any = None
FILES_TOTAL = -1
INVALID_TOTAL = 0
SUSPICIOUS_TOTAL = 0


def main() -> None:
    """
    Entry point.
    """
    global ARGS, FILES_TOTAL

    try:
        warnings.resetwarnings()
        warnings.simplefilter("ignore")

        ARGS = retrieve_args()

        with yaspin() as sp:
            FILES_TOTAL, src_total = audiofiles_count(ARGS.src_dir, sp)
        if ARGS.count:
            print(f" {DONE_ICON} Valid: {FILES_TOTAL} file(s)", end="")
            print(f"; Volume: {human_fine(src_total)}", end="")
            if FILES_TOTAL > 0:
                print(f"; Average: {human_fine(src_total // FILES_TOTAL)}", end="")
            print("")
        else:
            copy_album()

        if INVALID_TOTAL > 0:
            print(f" {INVALID_ICON} Broken: {INVALID_TOTAL} file(s)")
        if SUSPICIOUS_TOTAL > 0:
            print(f" {SUSPICIOUS_ICON} Suspicious: {SUSPICIOUS_TOTAL} file(s)")

    except KeyboardInterrupt as ctrl_c:
        sys.exit(ctrl_c)


if __name__ == "__main__":
    main()
