"""
Audio album builder as a library. See description.
"""

PY_VERSION = (3, 6, 0)

import sys

assert sys.version_info >= PY_VERSION, f"Python {PY_VERSION} or later required."

from typing import List, Tuple, Iterator, Any
import mutagen as mt
import os
import re
import shutil
import argparse
import warnings
import inspect
import functools as ft
from time import perf_counter
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


def _path_compare(path_x: Path, path_y: Path) -> Ord:
    """
    Compares two paths (directories).
    """
    return (
        strcmp_c(str(path_x), str(path_y))
        if _ARGS.sort_lex
        else strcmp_naturally(str(path_x), str(path_y))
    )


def _file_compare(path_x: Path, path_y: Path) -> Ord:
    """
    Compares two paths, filenames only, ignoring extensions.
    """
    return (
        strcmp_c(path_x.stem, path_y.stem)
        if _ARGS.sort_lex
        else strcmp_naturally(path_x.stem, path_y.stem)
    )


def _mutagen_file(name: Path, spinner=None):
    """
    Returns Mutagen thing, if name looks like an audio file path, else returns None.
    """
    global _INVALID_TOTAL, _SUSPICIOUS_TOTAL

    if _ARGS.file_type and not has_ext_of(name, _ARGS.file_type):
        return None

    name_to_print: str = str(name) if _ARGS.verbose else name.name

    try:
        file = mt.File(name, easy=True)
    except mt.MutagenError as mt_error:
        if spinner:
            spinner.write(f" {INVALID_ICON} >>{mt_error}>> {name_to_print}")
            _INVALID_TOTAL += 1
        return None

    if spinner and file is None and has_ext_of(name, *KNOWN_EXTENSIONS):
        spinner.write(f" {SUSPICIOUS_ICON} {name_to_print}")
        _SUSPICIOUS_TOTAL += 1
    return file


def _is_audiofile(name: Path, spinner=None) -> bool:
    """
    Returns True, if name is an audio file, else returns False.
    """
    if name.is_file():
        file = _mutagen_file(name, spinner)
        if file is not None:
            return True
    return False


def _list_dir_groom(abs_path: Path, rev=False) -> Tuple[List[Path], List[Path]]:
    """
    Returns a tuple of: (0) naturally sorted list of
    offspring directory names (1) naturally sorted list
    of offspring file names.
    """
    lst = os.listdir(abs_path)
    dirs = sorted(
        [Path(x) for x in lst if (abs_path / x).is_dir()],
        key=ft.cmp_to_key(
            (lambda xp, yp: -_path_compare(xp, yp)) if rev else _path_compare
        ),
    )
    files = sorted(
        [Path(x) for x in lst if _is_audiofile(abs_path / x)],
        key=ft.cmp_to_key(
            (lambda xf, yf: -_file_compare(xf, yf)) if rev else _file_compare
        ),
    )
    return dirs, files


def _decorate_dir_name(i: int, path: Path) -> str:
    """
    Prepends decimal i to path name.
    """
    return ("" if _ARGS.strip_decorations else (str(i).zfill(3) + "-")) + path.name


def _artist(*, prefix="", suffix="") -> str:
    """
    Generates Artist prefix for a directory/file name.
    """
    if _ARGS.artist_tag:
        return prefix + _ARGS.artist_tag + suffix
    return ""


def _decorate_file_name(i: int, dst_step: List[str], path: Path) -> str:
    """
    Prepends zero padded decimal i to path name.
    """
    if _ARGS.strip_decorations:
        return path.name
    prefix = str(i).zfill(len(str(_FILES_TOTAL))) + (
        "-" + "-".join(dst_step) + "-"
        if _ARGS.prepend_subdir_name and not _ARGS.tree_dst and len(dst_step) > 0
        else "-"
    )
    return prefix + (
        _ARGS.unified_name + _artist(prefix=" - ") + path.suffix
        if _ARGS.unified_name
        else path.name
    )


def _walk_file_tree(
    src_dir: Path, dst_root: Path, fcount: List[int], dst_step: List[str]
) -> Iterator[Tuple[int, Path, Path, str]]:
    """
    Recursively traverses the source directory and yields a tuple of copying attributes;
    the destination directory and file names get decorated according to options.
    """
    dirs, files = _list_dir_groom(src_dir, _ARGS.reverse)

    def dir_flat(dirs):
        for directory in dirs:
            step = list(dst_step)
            step.append(directory.name)
            yield from _walk_file_tree(src_dir / directory, dst_root, fcount, step)

    def file_flat(files):
        for file in files:
            yield fcount[0], src_dir / file, dst_root, _decorate_file_name(
                fcount[0], dst_step, file
            )
            fcount[0] += -1 if _ARGS.reverse else 1

    def reverse(i, lst):
        return len(lst) - i if _ARGS.reverse else i + 1

    def dir_tree(dirs):
        for i, directory in enumerate(dirs):
            step = list(dst_step)
            step.append(_decorate_dir_name(reverse(i, dirs), directory))
            yield from _walk_file_tree(src_dir / directory, dst_root, fcount, step)

    def file_tree(files):
        for i, file in enumerate(files):
            yield fcount[0], src_dir / file, dst_root.joinpath(
                *dst_step
            ), _decorate_file_name(reverse(i, files), dst_step, file)
            fcount[0] += -1 if _ARGS.reverse else 1

    dir_fund, file_fund = (
        (dir_tree, file_tree) if _ARGS.tree_dst else (dir_flat, file_flat)
    )

    if _ARGS.reverse:
        yield from file_fund(files)
        yield from dir_fund(dirs)
    else:
        yield from dir_fund(dirs)
        yield from file_fund(files)


def _audiofiles_count(directory: Path, spinner=None) -> Tuple[int, int]:
    """
    Returns full recursive count of audiofiles in directory.
    """
    cnt, size = 0, 0

    for root, _dirs, files in os.walk(directory):
        for name in files:
            abs_path = Path(root) / name
            if _is_audiofile(abs_path, spinner):
                if spinner and cnt % 10 == 0:
                    spinner.text = name
                cnt += 1
                size += abs_path.stat().st_size
    return cnt, size


def _album() -> Iterator[Tuple[int, Path, Path, str]]:
    """
    Sets up boilerplate required by the options and returns the ammo belt generator
    of (src, dst) pairs.
    """
    prefix = (str(_ARGS.album_num).zfill(2) + "-") if _ARGS.album_num else ""
    base_dst = prefix + (
        _artist(suffix=" - ") + _ARGS.unified_name
        if _ARGS.unified_name
        else _ARGS.src_dir.name
    )

    executive_dst = _ARGS.dst_dir / ("" if _ARGS.drop_dst else base_dst)

    if _FILES_TOTAL < 1:
        _show(
            f'There are no supported audio files in the source directory "{_ARGS.src_dir}".'
        )
        sys.exit(1)

    if not _ARGS.drop_dst and not _ARGS.dry_run:
        if executive_dst.exists():
            if _ARGS.overwrite:
                try:
                    shutil.rmtree(executive_dst)
                except FileNotFoundError:
                    _show(f'Failed to remove "{executive_dst}".')
                    sys.exit(1)
            else:
                _show(f'Destination directory "{executive_dst}" already exists.')
                sys.exit(1)
        executive_dst.mkdir()

    return _walk_file_tree(
        _ARGS.src_dir, executive_dst, [_FILES_TOTAL if _ARGS.reverse else 1], []
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
    >>> human_rough(1024 ** 4)
    '1TB'
    """
    return (
        str(bytes) + units[0] if bytes < 1024 else human_rough(bytes >> 10, units[1:])
    )


def human_fine(bytes: int) -> str:
    """
    Returns a human readable string representation of bytes, nicely rounded.

    >>> human_fine(42)
    '42'
    >>> human_fine(1800)
    '2kB'
    >>> human_fine(123456789)
    '117.7MB'
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


def _copy_album() -> None:
    """
    Runs through the ammo belt and does copying, in the reverse order if necessary.
    """

    def set_tags(i: int, source: Path, path: Path) -> None:
        def make_title(tagging: str) -> str:
            if _ARGS.file_title_num:
                return str(i) + ">" + source.stem
            if _ARGS.file_title:
                return source.stem
            return str(i) + " " + tagging

        audio = _mutagen_file(path)
        if audio is None:
            return

        if not _ARGS.drop_tracknumber:
            audio["tracknumber"] = str(i) + "/" + str(_FILES_TOTAL)
        if _ARGS.artist_tag and _ARGS.album_tag:
            audio["title"] = make_title(
                make_initials(_ARGS.artist_tag) + " - " + _ARGS.album_tag
            )
            audio["artist"] = _ARGS.artist_tag
            audio["album"] = _ARGS.album_tag
        elif _ARGS.artist_tag:
            audio["title"] = make_title(_ARGS.artist_tag)
            audio["artist"] = _ARGS.artist_tag
        elif _ARGS.album_tag:
            audio["title"] = make_title(_ARGS.album_tag)
            audio["album"] = _ARGS.album_tag
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
        if not _ARGS.dry_run:
            dst_path.mkdir(parents=True, exist_ok=True)
            copy_and_set_via_tmp(i, src, dst)
            dst_bytes = dst.stat().st_size
        if _ARGS.verbose:
            _show(f"{i:>4}/{_FILES_TOTAL} {COLUMN_ICON} {dst}", end="")
            if dst_bytes != src_bytes:
                if dst_bytes == 0:
                    _show(f"  {COLUMN_ICON} {human_fine(src_bytes)}", end="")
                else:
                    _show(f"  {COLUMN_ICON} {(dst_bytes - src_bytes):+d}", end="")
            _show("")
        else:
            _show(".", end="", flush=True)
        return src_bytes, dst_bytes

    if not _ARGS.verbose:
        _show("Starting ", end="", flush=True)

    src_total, dst_total, files_total = 0, 0, 0

    for entry in _album():
        src_bytes, dst_bytes = copy_file(entry)
        src_total += src_bytes
        dst_total += dst_bytes
        files_total += 1

    _show(f" {DONE_ICON} Done ({files_total}, {human_fine(dst_total)}", end="")
    if _ARGS.dry_run:
        _show(f"; Volume: {human_fine(src_total)}", end="")
    _show(f"; {(perf_counter() - _START_TIME):.1f}s).")
    if files_total != _FILES_TOTAL:
        _show(f"Fatal error. files_total: {files_total}, _FILES_TOTAL: {_FILES_TOTAL}")


def _retrieve_args(argv: List[str]) -> Any:
    """
    Parses the command line and returns a collection of arguments.
    """
    parser = argparse.ArgumentParser(
        description=f"""
    Damastes a.k.a. Procrustes is a CLI utility for copying directories and subdirectories
    containing supported audio files in sequence, naturally sorted.
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
        version=_APP_VERSION,
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
        help="without actually modifying anything (trumps -w, too)",
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
        "-e",
        "--file-type",
        help="accept only audio files of the specified type (e.g. -e mp3)",
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
    args = parser.parse_args(argv)
    args.src_dir = Path(
        args.src_dir
    ).absolute()  # Takes care of the trailing slash, too.
    args.dst_dir = Path(args.dst_dir).absolute()

    if not args.src_dir.is_dir():
        _show(f'Source directory "{args.src_dir}" is not there.')
        sys.exit(1)
    if not args.dst_dir.is_dir():
        _show(f'Destination path "{args.dst_dir}" is not there.')
        sys.exit(1)

    if args.unified_name and args.album_tag is None:
        args.album_tag = args.unified_name

    return args


def _show(string: str, end="\n", file=sys.stdout, flush=False) -> None:
    if _APP_VERSION:
        return print(string, end=end, file=file, flush=flush)


def list_safe_imports(*, unsafe: List[str] = ["run"]) -> List[str]:
    """
    Returns a list of general purpose functions without side effects,
    presumably safe to import and run anywhere. The presence of a
    doctest is usually a good sign of safety :)

    >>> 'list_safe_imports' in list_safe_imports()
    True
    """
    return [
        m[0]
        for m in inspect.getmembers(sys.modules[__name__], inspect.isfunction)
        if __name__ == m[1].__module__ and m[0] not in unsafe and m[0][0] != "_"
    ]


NB = "\U0001f53b"
INVALID_ICON = "\U0000274c"
SUSPICIOUS_ICON = "\U00002754"
DONE_ICON = "\U0001f7e2"
COLUMN_ICON = "\U00002714"
KNOWN_EXTENSIONS = ["MP3", "OGG", "M4A", "M4B", "FLAC", "APE"]

_ARGS: Any = None
_FILES_TOTAL = -1
_INVALID_TOTAL = 0
_SUSPICIOUS_TOTAL = 0
_APP_VERSION = ""
_START_TIME = 0.0


def _reset_all() -> None:
    global _ARGS
    global _FILES_TOTAL
    global _INVALID_TOTAL
    global _SUSPICIOUS_TOTAL
    global _APP_VERSION
    global _START_TIME

    _ARGS = None
    _FILES_TOTAL = -1
    _INVALID_TOTAL = 0
    _SUSPICIOUS_TOTAL = 0
    _APP_VERSION = ""
    _START_TIME = perf_counter()


def run(*, argv: List[str] = sys.argv[1:], version="") -> int:
    """
    Runs the whole Procrustes business according to argv options.
    Non-empty version means full console output required by
    a command line utility.
    """
    global _ARGS, _FILES_TOTAL, _APP_VERSION

    try:
        warnings.resetwarnings()
        warnings.simplefilter("ignore")

        _reset_all()
        _APP_VERSION = version
        _ARGS = _retrieve_args(argv)

        if _APP_VERSION:
            with yaspin() as sp:
                _FILES_TOTAL, src_total = _audiofiles_count(_ARGS.src_dir, sp)
        else:
            _FILES_TOTAL, src_total = _audiofiles_count(_ARGS.src_dir)

        if _ARGS.count:
            _show(f" {DONE_ICON} Valid: {_FILES_TOTAL} file(s)", end="")
            _show(f"; Volume: {human_fine(src_total)}", end="")
            if _FILES_TOTAL > 1:
                _show(f"; Average: {human_fine(src_total // _FILES_TOTAL)}", end="")
            _show(f"; Time: {(perf_counter() - _START_TIME):.1f}s")
        else:
            _copy_album()

        if _INVALID_TOTAL > 0:
            _show(f" {INVALID_ICON} Broken: {_INVALID_TOTAL} file(s)")
        if _SUSPICIOUS_TOTAL > 0:
            _show(f" {SUSPICIOUS_ICON} Suspicious: {_SUSPICIOUS_TOTAL} file(s)")

    except KeyboardInterrupt:
        _show("Aborted manually.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run(version="Procrustes running..."))
