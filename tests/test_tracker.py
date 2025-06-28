import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from tracker import ByteTracker


def test_bytracker_id_persistence():
    tracker = ByteTracker(iou_threshold=0.1, decay_time=1.0)
    first = tracker.update([(0, 0, 10, 10)], 0.0)
    tid = next(iter(first))
    # no detection frame within decay time
    tracker.update([], 0.5)
    second = tracker.update([(1, 1, 11, 11)], 0.6)
    assert tid in second


def test_bytracker_expiry():
    tracker = ByteTracker(iou_threshold=0.1, decay_time=0.5)
    first = tracker.update([(0, 0, 10, 10)], 0.0)
    tid = next(iter(first))
    tracker.update([], 1.0)
    second = tracker.update([(0, 0, 10, 10)], 1.1)
    assert list(second.keys())[0] != tid
