"""Deprecated wrapper for :mod:`carspeed.cli`.

This file remains for backward compatibility and simply forwards
to :func:`carspeed.cli.main`.
"""

from carspeed.cli import main

if __name__ == "__main__":  # pragma: no cover - wrapper
    main()
