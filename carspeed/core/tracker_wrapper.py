"""Abstract interface for tracker implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


Point = Tuple[float, float]
Box = Tuple[int, int, int, int]


class BaseTracker(ABC):
    """Interface for tracker wrappers."""

    @abstractmethod
    def update(self, boxes: List[Box], ts: float) -> Dict[int, Point]:
        """Update with detections and return mapping of track id to centroid."""
        raise NotImplementedError
