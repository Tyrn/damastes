"""
Audio album builder.
"""

import sys
import functools
import click
from . import __version__
from .run import _run  # type: ignore
from .run import _set_args_click  # type: ignore


def _steady_parameters(func):
    @click.option(
        "-v",
        "--verbose",
        is_flag=True,
        help=click.style("Verbose output", fg="green") + ".",
    )
    @click.option(
        "-d", "--drop-tracknumber", is_flag=True, help="Do not set track numbers."
    )
    @click.option(
        "-s",
        "--strip-decorations",
        is_flag=True,
        help="Strip file and directory name decorations.",
    )
    @click.option(
        "-f", "--file-title", is_flag=True, help="Use file name for title tag."
    )
    @click.option(
        "-F",
        "--file-title-num",
        is_flag=True,
        help="Use numbered file name for title tag.",
    )
    @click.option(
        "-x", "--sort-lex", is_flag=True, help="Sort files lexicographically."
    )
    @click.option(
        "-t",
        "--tree-dst",
        is_flag=True,
        help="Retain the tree structure of the source album at destination.",
    )
    @click.option(
        "-p", "--drop-dst", is_flag=True, help="Do not create destination directory."
    )
    @click.option(
        "-r",
        "--reverse",
        is_flag=True,
        help="Copy files in reverse order (number one file is the last to be copied).",
    )
    @click.option(
        "-w",
        "--overwrite",
        is_flag=True,
        help="Silently remove existing destination directory ("
        + click.style("not", fg="red")
        + " recommended).",
    )
    @click.option(
        "-y",
        "--dry-run",
        is_flag=True,
        help="Without actually modifying anything (trumps "
        + click.style("-w", fg="yellow")
        + ", too).",
    )
    @click.option("-c", "--count", is_flag=True, help="Just count the files.")
    @click.option(
        "-i",
        "--prepend-subdir-name",
        is_flag=True,
        help="Prepend current subdirectory name to a file name.",
    )
    @click.option(
        "-e",
        "--file-type",
        type=str,
        default=None,
        help="Accept only specified audio files (e.g. "
        + click.style("-e flac", fg="yellow")
        + ", or even "
        + click.style("-e '*64kb.mp3'", fg="yellow")
        + ").",
    )
    @click.option(
        "-u",
        "--unified-name",
        type=str,
        default=None,
        help="Destination "
        + click.style("directory name", fg="green")
        + " and "
        + click.style("file names", fg="green")
        + " are based on TEXT, file extensions retained; also "
        + click.style("album tag", fg="green")
        + ", if the latter is not specified explicitly.",
    )
    @click.option(
        "-a",
        "--artist",
        type=str,
        default=None,
        help=click.style("Artist tag", fg="green") + ".",
    )
    @click.option(
        "-m",
        "--album",
        type=str,
        default=None,
        help=click.style("Album tag", fg="green") + ".",
    )
    @click.option(
        "-b",
        "--album-num",
        type=int,
        default=None,
        help="0..99; prepend INTEGER to the destination root directory name.",
    )
    @click.option("--context", is_flag=True, hidden=True, help="Print clean context.")
    @click.option("--no-console", is_flag=True, hidden=True, help="No console mode.")
    @click.argument("src_dir", type=click.Path(exists=True, resolve_path=True))
    @click.argument("dst_dir", type=click.Path(exists=True, resolve_path=True))
    @functools.wraps(func)
    def parameters(**kwargs):
        func(**kwargs)

    return parameters


def _print_clean_context_params() -> None:
    print("CLEAN_CONTEXT_PARAMS = {")
    count = 0
    for k, v in click.get_current_context().params.items():
        print(f'    "{k}": {False if isinstance(v, bool) else None},')
        count += 1
    print(f"}}  # {count} of them.")


@click.command()
@click.help_option("-h", "--help")
@click.version_option(__version__, "-V", "--version")
@_steady_parameters
def main(**kwargs) -> int:
    """
    Damastes a.k.a. Procrustes is a CLI utility for copying directories and subdirectories
    containing supported audio files in sequence, naturally sorted.
    The end result is a "flattened" copy of the source subtree. "Flattened" means
    that only a namesake of the root source directory is created, where all the files get
    copied to, names prefixed with a serial number. Tag "Track Number"
    is set, tags "Title", "Artist", and "Album" can be replaced optionally.
    The writing process is strictly sequential: either starting with the number one file,
    or in the reverse order. This can be important for some mobile devices.
    \U0000274c Broken media;
    \U00002754 Suspicious media.

    Example:

    robinson-crusoe $ damastes -va 'Daniel "Goldeneye" Defoe' -u 'Robinson Crusoe' .
    /run/media/player
    """
    _set_args_click()

    from .run import _ARGS  # type: ignore

    if _ARGS.context and not _ARGS.no_console:
        _print_clean_context_params()
        return 0

    return _run()


if __name__ == "__main__":
    sys.exit(main())
