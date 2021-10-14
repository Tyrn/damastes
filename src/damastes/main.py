"""
Audio album builder.
"""

import sys
import click
from . import __version__
from .run import _run  # type: ignore
from .run import _steady_parameters  # type: ignore
from .run import _set_args_click  # type: ignore


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
    return _run()


if __name__ == "__main__":
    sys.exit(main())
