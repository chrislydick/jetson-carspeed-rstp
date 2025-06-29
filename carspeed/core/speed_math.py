"""Helpers for converting positions to speed measurements."""

from __future__ import annotations

from math import hypot
from typing import List, Sequence, Tuple

Point = Tuple[float, float]


def pixels_to_meters(pixels: float, ppm: float) -> float:
    """Convert a pixel distance to meters using ``ppm`` (pixels per meter)."""
    return pixels / ppm


def pixel_distance(a: Point, b: Point) -> float:
    """Return Euclidean distance between two points in pixels."""
    return hypot(a[0] - b[0], a[1] - b[1])


def instant_speed(prev: Point, curr: Point, dt: float, ppm: float) -> float:
    """Instantaneous speed in meters/second between two samples."""
    dist = pixels_to_meters(pixel_distance(prev, curr), ppm)
    return dist / dt if dt > 0 else 0.0


def rolling_speed(
    centroids: Sequence[Point], timestamps: Sequence[float], ppm: float, window: int = 1
) -> List[float]:
    """Return rolling average speed values in meters/second."""
    if len(centroids) != len(timestamps):
        raise ValueError("centroids and timestamps must align")
    if len(centroids) < 2:
        return []

    speeds: List[float] = []
    for i in range(1, len(centroids)):
        v = instant_speed(
            centroids[i - 1], centroids[i], timestamps[i] - timestamps[i - 1], ppm
        )
        speeds.append(v)

    if window > 1:
        smooth: List[float] = []
        for i in range(len(speeds)):
            start = max(0, i - window + 1)
            smooth.append(sum(speeds[start : i + 1]) / (i - start + 1))
        speeds = smooth
    return speeds
