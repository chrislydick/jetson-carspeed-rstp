"""Utility helpers for RTSP sources."""

from __future__ import annotations

from gi.repository import Gst

Gst.init(None)


def latency_source(uri: str) -> Gst.Element:
    """Return an RTSP source element configured with low latency."""
    desc = (
        f"rtspsrc location={uri} latency=100 ! rtph265depay ! h265parse ! nvv4l2decoder"
    )
    return Gst.parse_launch(desc)
