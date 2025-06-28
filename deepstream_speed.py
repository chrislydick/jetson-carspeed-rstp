# -*- coding: utf-8 -*-
"""Compatibility wrapper for the carspeed CLI."""

from carspeed.cli import main
from carspeed.pipelines.deepstream import build_pipeline

__all__ = ["build_pipeline", "main"]


if __name__ == "__main__":
    main()
