"""
Audio album builder.
"""

from . import __version__
import sys
from procrustes import procrustes  # type: ignore


def main() -> int:
    return procrustes.main(stub=f"Damastes {__version__}")


if __name__ == "__main__":
    sys.exit(main())
