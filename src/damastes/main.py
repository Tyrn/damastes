"""
Audio album builder.
"""

import sys
from . import __version__
from . import run  # type: ignore


def main() -> int:
    """
    Entry point.
    """
    return run(version=f"Damastes {__version__}")


if __name__ == "__main__":
    sys.exit(main())
