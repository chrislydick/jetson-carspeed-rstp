"""Dataclasses for pipeline configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineOptions:
    """User facing configuration options."""

    uri: str
    config: str
    engine: str
    db: str
    ppm: float
    is_rtsp: bool
    homography: Optional[str] = None
    window: int = 3
    batch_size: int = 1
    width: int = 1280
    height: int = 720
