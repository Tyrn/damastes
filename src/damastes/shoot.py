"""
Audio album builder as a library. See description.
"""
import copy
import fnmatch
import functools
import inspect
import os
import re
import shutil
import sys
import warnings
from math import log
from pathlib import Path
from tempfile import mkstemp
from time import perf_counter
from typing import Iterator, List, Tuple

import mutagen
from yaspin import yaspin  # type: ignore

PY_VERSION = (3, 10, 0)

assert (
    sys.version_info >= PY_VERSION
), f"Python {PY_VERSION[0]}.{PY_VERSION[1]}.{PY_VERSION[2]} or later required."


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


def _mutagen_file(name: Path, spinner=None):  # pragma: no cover
    """
    Returns Mutagen thing, if name looks like an audio file path, else returns None.
    """
    global _INVALID_TOTAL, _SUSPICIOUS_TOTAL  # pylint:disable=global-statement
    ext = name.suffix.lstrip(".").upper()
    atp = _ARGS.file_type

    if atp:
        if "*" in atp or "?" in atp or "[" in atp:
            if not fnmatch.fnmatch(name.name, atp):
                return None
        else:
            if ext != atp.lstrip(".").upper():
                return None

    name_to_print: str = str(name) if _ARGS.verbose else name.name

    try:
        file = mutagen.File(name, easy=True)
    except mutagen.MutagenError as mt_error:
        if spinner:
            spinner.write(f" {INVALID_ICON} >>{mt_error}>> {name_to_print}")
        _INVALID_TOTAL += 1  # pylint:disable=undefined-variable
        return None

    if file is None and ext in KNOWN_EXTENSIONS:
        if spinner:
            spinner.write(f" {SUSPICIOUS_ICON} {name_to_print}")
        _SUSPICIOUS_TOTAL += 1  # pylint:disable=undefined-variable
    return file


def _is_audiofile(name: Path, spinner=None) -> bool:  # pragma: no cover
    """
    Returns True, if name is an audio file, else returns False.
    """
    if name.is_file():
        file = _mutagen_file(name, spinner)
        if file is not None:
            return True
    return False


def _artist_part(*, prefix="", suffix="") -> str:
    """
    Returns Artist, nicely shaped to be a part of a directory/file name.
    """
    if _ARGS.artist:
        return prefix + _ARGS.artist + suffix
    return ""


def _file_decorate(i: int, step_down: List[str], file: Path) -> str:
    """
    Prepends zero padded decimal i to path name.
    """
    if _ARGS.strip_decorations and _ARGS.tree_dst:
        return file.name
    prefix = str(i).zfill(len(str(_FILES_TOTAL))) + (
        "-[" + "][".join(step_down) + "]-"
        if _ARGS.prepend_subdir_name and not _ARGS.tree_dst and len(step_down) > 0
        else "-"
    )
    return prefix + (
        _ARGS.unified_name + _artist_part(prefix=" - ") + file.suffix
        if _ARGS.unified_name
        else file.name
    )


_DirWalkItem = Tuple[int, List[str], Path]
_DirWalkIterator = Iterator[_DirWalkItem]


def _dir_walk(
    src: Path, step_down: List[str], fcount: List[int]
) -> _DirWalkIterator:  # pragma: no cover
    """
    Walks down the src tree, accumulating step_down on each recursion level.
    Yields a tuple of:
    (index, list of subdirectories to be joined
    at destination if necessary, source audiofile name)
    """
    if _is_audiofile(src):
        dirs: List[Path] = []
        files: List[Path] = [Path(src.name)]
        src = src.parent
    else:
        lst = os.listdir(src)
        dirs = sorted(
            [Path(x) for x in lst if (src / x).is_dir()],
            key=functools.cmp_to_key(
                (lambda xp, yp: _path_compare(yp, xp))
                if _ARGS.reverse
                else _path_compare
            ),
        )
        files = sorted(
            [Path(x) for x in lst if _is_audiofile(src / x)],
            key=functools.cmp_to_key(
                (lambda xf, yf: _file_compare(yf, xf))
                if _ARGS.reverse
                else _file_compare
            ),
        )

    def walk_into(dirs: List[Path]) -> _DirWalkIterator:
        for directory in dirs:
            step = list(step_down)
            step.append(directory.name)
            yield from _dir_walk(src / directory, step, fcount)

    def walk_along(files: List[Path]) -> _DirWalkIterator:
        for file in files:
            yield fcount[0], step_down, file
            fcount[0] += fcount[1]  # [counter, const increment_by]

    if _ARGS.reverse:
        yield from walk_along(files)
        yield from walk_into(dirs)
    else:
        yield from walk_into(dirs)
        yield from walk_along(files)


def _audiofiles_count(
    directory: Path, spinner=None
) -> Tuple[int, int]:  # pragma: no cover
    """
    Returns full recursive count of audiofiles in directory.
    """
    if _is_audiofile(directory, spinner):
        return 1, directory.stat().st_size

    if directory.is_file():
        return 0, 0

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


def _dst_calculate() -> str:
    """
    Calculates destination directory, if any, to be appended to
    the destination path collected from the command line.
    """
    return (
        ""
        if _ARGS.drop_dst
        else (
            ((str(_ARGS.album_num).zfill(2) + "-") if _ARGS.album_num else "")
            + (
                _artist_part(suffix=" - ") + _ARGS.unified_name
                if _ARGS.unified_name
                else _ARGS.src.stem
                if _ARGS.src.is_file()
                else _ARGS.src.name
            )
        )
    )


def _album() -> _DirWalkIterator:  # pragma: no cover
    """
    Sets up boilerplate required by the options and returns the ammo belt generator of
    (index, list of subdirectories to be joined
    at destination if necessary, source audiofile name) tuples.
    """
    if _FILES_TOTAL < 1:
        _show(
            f" {WARNING_ICON} There are no supported audio files"
            + f' in the source directory "{_ARGS.src}".'
        )
        sys.exit(1)

    if not _ARGS.drop_dst and not _ARGS.dry_run:
        if _ARGS.dst_dir.exists():
            if _ARGS.overwrite:
                try:
                    shutil.rmtree(_ARGS.dst_dir)
                except FileNotFoundError:
                    _show(f' {WARNING_ICON} Failed to remove "{_ARGS.dst_dir}".')
                    sys.exit(1)
            else:
                _show(
                    f' {WARNING_ICON} Target directory "{_ARGS.dst_dir}" already exists.'
                )
                sys.exit(1)
        _ARGS.dst_dir.mkdir()

    return _dir_walk(_ARGS.src, [], [_FILES_TOTAL, -1] if _ARGS.reverse else [1, 1])


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
        quotient = float(bytes) / 1024**exponent
        unit, num_decimals = unit_list[exponent]
        return f"{{:.{num_decimals}f}}{{}}".format(quotient, unit)
    if bytes == 0:
        return "0"
    return "1" if bytes == 1 else f"human_fine error; bytes: {bytes}"


def _album_copy() -> None:  # pragma: no cover
    """
    Runs through the ammo belt and does copying, in the reverse order if necessary.
    """

    artist_initials: str = initials(_ARGS.artist) if _ARGS.artist else ""

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
        if _ARGS.artist and _ARGS.album:
            audio["title"] = make_title(artist_initials + " - " + _ARGS.album)
            audio["artist"] = _ARGS.artist
            audio["album"] = _ARGS.album
        elif _ARGS.artist:
            audio["title"] = make_title(_ARGS.artist)
            audio["artist"] = _ARGS.artist
        elif _ARGS.album:
            audio["title"] = make_title(_ARGS.album)
            audio["album"] = _ARGS.album
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

    def file_copy(entry: _DirWalkItem) -> Tuple[int, int]:
        i, step_down, src_file = entry

        src = _ARGS.src.joinpath(*step_down) / src_file
        dst_path = (
            _ARGS.dst_dir.joinpath(*step_down) if _ARGS.tree_dst else _ARGS.dst_dir
        )
        dst = dst_path / _file_decorate(i, step_down, src_file)

        src_bytes, dst_bytes = src.stat().st_size, 0

        if not _ARGS.dry_run:
            dst_path.mkdir(parents=True, exist_ok=True)
            if dst.is_file():
                _SHORT_LOG.append(
                    f'File "{dst.name}" already copied. Review your options.'
                )
            else:
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
        src_bytes, dst_bytes = file_copy(entry)
        src_total += src_bytes
        dst_total += dst_bytes
        files_total += 1

    _show(f" {DONE_ICON} Done ({files_total}, {human_fine(dst_total)}", end="")
    if _ARGS.dry_run:
        _show(f"; Volume: {human_fine(src_total)}", end="")
    _show(f"; {(perf_counter() - _START_TIME):.1f}s).")
    if files_total != _FILES_TOTAL:
        _show(f"Fatal error. files_total: {files_total}, _FILES_TOTAL: {_FILES_TOTAL}")


def _show(
    string: str, *, end="\n", file=sys.stdout, flush=False
) -> None:  # pragma: no cover
    if not _ARGS.no_console:
        return print(string, end=end, file=file, flush=flush)


def safe_imports(*, unsafe: List[str] = ["run"]) -> List[str]:
    """
    Returns a list of general purpose functions without side effects,
    presumably safe to import and run anywhere. The presence of a
    doctest is usually a good sign of safety :)

    >>> 'safe_imports' in safe_imports()
    True
    """
    return [
        m[0]
        for m in inspect.getmembers(sys.modules[__name__], inspect.isfunction)
        if __name__ == m[1].__module__ and m[0] not in unsafe and m[0][0] != "_"
    ]


def initials(authors: str) -> str:
    """
    Reduces authors to initials.

    >>> initials('Ignacio "Castigador" Vazquez-Abrams, Estefania Cassingena Navone')
    'I.V-A.,E.C.N.'
    >>> initials("Rory O'Connor, Seumas MacManus, Christine McConnell")
    "R.O'C.,S.MacM.,C.McC."
    >>> initials("Jason dinAlt, Charles d'Artagnan, D'Arcy McNickle, Ross Macdonald")
    "J.dinA.,C.d'A.,D'A.McN.,R.M."
    """

    def form_initial(name: str) -> str:
        if len(cut := name.split("'")) > 1 and cut[1]:  # Deal with '.
            if cut[1][0].islower() and cut[0]:
                return cut[0][0].upper()
            return cut[0] + "'" + cut[1][0]

        if len(name) > 1:  # Deal with prefixes.
            match name:
                case "Старший":
                    return "Ст"
                case "Младший":
                    return "Мл"
                case "Ст" | "ст" | "Sr" | "Мл" | "мл" | "Jr":
                    return name

            prefix = name[0]
            for ch in name[1:]:
                prefix += ch
                if ch.isupper():
                    return prefix

        if name in [
            "von",
            "фон",
            "van",
            "ван",
            "der",
            "дер",
            "til",
            "тиль",
            "zu",
            "цу",
            "zum",
            "цум",
            "zur",
            "цур",
            "af",
            "аф",
            "of",
            "из",
            "da",
            "да",
            "de",
            "де",
            "des",
            "дез",
            "del",
            "дель",
            "di",
            "ди",
            "dos",
            "душ",
            "дос",
            "du",
            "дю",
            "la",
            "ла",
            "ля",
            "le",
            "ле",
            "haut",
            "от",
            "the",
        ]:
            return name[0]
        return name[0].upper()

    return COMMA.join(
        HYPH.join(
            SEP.join(form_initial(name) for name in RE_BY_SEP.split(barrel) if name)
            for barrel in author.split(HYPH)
            if barrel.replace(SEP, "").strip()
        )
        + SEP
        for author in RE_QUOTED_SUBSTRING.sub(" ", authors)
        .replace('"', " ")
        .split(COMMA)
        if author.replace(SEP, "").replace(HYPH, "").strip()
    )


SEP = "."
HYPH = "-"
COMMA = ","
RE_BY_SEP = re.compile(rf"[\s{SEP}]+")
RE_BY_HYPH = re.compile(rf"\s*(?:{HYPH}\s*)+")
RE_QUOTED_SUBSTRING = re.compile(r"\"(?:\\.|[^\"\\])*\"")

WARNING_ICON = "\U0001f4a7"
INVALID_ICON = "\U0000274c"
SUSPICIOUS_ICON = "\U00002754"
DONE_ICON = "\U0001f7e2"
COLUMN_ICON = "\U00002714"
KNOWN_EXTENSIONS = ["MP3", "OGG", "M4A", "M4B", "OPUS", "WMA", "FLAC", "APE"]
CLEAN_CONTEXT_PARAMS = {
    "context": False,
    "verbose": False,
    "src": None,
    "dst_dir": None,
    "drop_tracknumber": False,
    "strip_decorations": False,
    "file_title": False,
    "file_title_num": False,
    "sort_lex": False,
    "tree_dst": False,
    "drop_dst": False,
    "reverse": False,
    "overwrite": False,
    "dry_run": False,
    "count": False,
    "prepend_subdir_name": False,
    "file_type": None,
    "unified_name": None,
    "artist": None,
    "album": None,
    "album_num": None,
    "no_console": False,
}  # 22 of them.


class RestrictedDotDict(dict):  # pragma: no cover
    """
    Enables access to dictionary entries via dot notation.
    An attempt at adding a new key raises an exception.
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as k:
            raise AttributeError(k)

    def __setattr__(self, key, value):
        try:
            self[key]
        except KeyError as k:
            raise AttributeError(k)
        self[key] = value

    def __repr__(self):
        return "<RestrictedDotDict " + dict.__repr__(self) + ">"


_ARGS = RestrictedDotDict()

_FILES_TOTAL = -1
_INVALID_TOTAL = 0
_SUSPICIOUS_TOTAL = 0
_START_TIME = 0.0
_SHORT_LOG: List[str] = []


def _run() -> int:  # pragma: no cover
    """
    Runs the whole Procrustes business according to
    preset context.

    To be called once either from main() or from run(),
    after setting the context.
    """
    global _FILES_TOTAL
    global _INVALID_TOTAL
    global _SUSPICIOUS_TOTAL
    global _START_TIME
    global _SHORT_LOG

    _FILES_TOTAL = -1
    _INVALID_TOTAL = 0
    _SUSPICIOUS_TOTAL = 0
    _START_TIME = perf_counter()
    _SHORT_LOG = []

    # Tweak context presumably set by main() or run().
    _ARGS.src = Path(_ARGS.src).absolute()  # Takes care of the trailing slash, too.
    _ARGS.dst_dir = Path(_ARGS.dst_dir).absolute()

    if not _ARGS.src.is_dir() and not _ARGS.src.is_file():
        _show(f' {WARNING_ICON} Source directory "{_ARGS.src}" is not there.')
        sys.exit(1)
    if not _ARGS.dst_dir.is_dir():
        _show(f' {WARNING_ICON} Target directory "{_ARGS.dst_dir}" is not there.')
        sys.exit(1)
    _ARGS.dst_dir = _ARGS.dst_dir / _dst_calculate()

    if (
        not _ARGS.count
        and not _ARGS.src.is_file()
        and _ARGS.dst_dir.is_relative_to(_ARGS.src)
    ):
        dst_msg = f'Target directory "{_ARGS.dst_dir}"'
        src_msg = f'is inside source "{_ARGS.src}"'
        if _ARGS.dry_run:
            _SHORT_LOG.append(dst_msg)
            _SHORT_LOG.append(src_msg)
            _SHORT_LOG.append("It won't run.")
        else:
            _show(f" {WARNING_ICON} {dst_msg}")
            _show(f" {WARNING_ICON} {src_msg}")
            _show(f" {WARNING_ICON} No go.")
            sys.exit(1)

    if _ARGS.unified_name and _ARGS.album is None:
        _ARGS.album = _ARGS.unified_name

    try:
        warnings.resetwarnings()
        warnings.simplefilter("ignore")

        if _ARGS.no_console:
            _FILES_TOTAL, bytes_total = _audiofiles_count(_ARGS.src)
        else:
            with yaspin() as sp:
                _FILES_TOTAL, bytes_total = _audiofiles_count(_ARGS.src, sp)

        if _ARGS.count:
            _show(
                f" {DONE_ICON if _FILES_TOTAL else WARNING_ICON}"
                + f" Valid: {_FILES_TOTAL} file(s)",
                end="",
            )
            _show(f"; Volume: {human_fine(bytes_total)}", end="")
            if _FILES_TOTAL > 1:
                _show(f"; Average: {human_fine(bytes_total // _FILES_TOTAL)}", end="")
            _show(f"; Time: {(perf_counter() - _START_TIME):.1f}s")
        else:
            _INVALID_TOTAL = 0
            _SUSPICIOUS_TOTAL = 0

            _album_copy()

        if _INVALID_TOTAL > 0:
            _show(f" {INVALID_ICON} Broken: {_INVALID_TOTAL} file(s)")
        if _SUSPICIOUS_TOTAL > 0:
            _show(f" {SUSPICIOUS_ICON} Suspicious: {_SUSPICIOUS_TOTAL} file(s)")

        for line in _SHORT_LOG:
            _show(f" {WARNING_ICON} {line}")
        _SHORT_LOG.clear()

    except KeyboardInterrupt:
        _show(f" {WARNING_ICON} Aborted manually.", file=sys.stderr)
        return 1

    return 0


def _set_args_click(context_params: dict) -> None:  # pragma: no cover
    """
    To be called once from main() before _run().
    """
    global _ARGS

    _ARGS = RestrictedDotDict(copy.deepcopy(context_params))


def run(**kwargs) -> int:  # pragma: no cover
    """
    Sets up context parameters manually via kwargs
    and runs the whole Procrustes business.

    To be used from Python code.
    """
    global _ARGS

    _ARGS = RestrictedDotDict(copy.deepcopy(CLEAN_CONTEXT_PARAMS))
    for k, v in kwargs.items():
        if k not in _ARGS:
            _show(f' {WARNING_ICON} Nonexistent parameter "{k}"')
            return 1
        _ARGS[k] = v

    return _run()


if __name__ == "__main__":  # pragma: no cover
    print(
        f" {WARNING_ICON} Module [{Path(__file__).name}] is not runnable.",
        file=sys.stderr,
    )
    sys.exit(1)
