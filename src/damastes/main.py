"""
Audio album builder.
"""

from . import __version__
import sys
from procrustes.run import run  # type: ignore


def main() -> int:
    """
    Entry point.
    """
    return run(version=f"Damastes {__version__}")


if __name__ == "__main__":
    sys.exit(main())
