from typing import List, Tuple


class VehicleTrack:
    def __init__(self, box: Tuple[int, int, int, int], ts: float, tid: int):
        self.box = box
        self.last_ts = ts
        self.id = tid
        self.center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def _iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = float((x2 - x1) * (y2 - y1))
    area_a = float((box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
    area_b = float((box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
    return inter / (area_a + area_b - inter)


class ByteTracker:
    """Very small ByteTrack-inspired tracker."""

    def __init__(self, iou_threshold: float = 0.3, decay_time: float = 1.0):
        self.iou_threshold = iou_threshold
        self.decay_time = decay_time
        self.tracks = []
        self.next_id = 0

    def update(self, detections: List[Tuple[int, int, int, int]], ts: float):
        # remove expired tracks
        self.tracks = [t for t in self.tracks if ts - t.last_ts <= self.decay_time]

        assignments = {}
        used = set()
        for box in detections:
            best_iou = self.iou_threshold
            best_track = None
            for track in self.tracks:
                if track in used:
                    continue
                iou = _iou(box, track.box)
                if iou > best_iou:
                    best_iou = iou
                    best_track = track
            if best_track is None:
                tid = self.next_id
                self.next_id += 1
                best_track = VehicleTrack(box, ts, tid)
                self.tracks.append(best_track)
            else:
                best_track.box = box
                best_track.center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                best_track.last_ts = ts
            used.add(best_track)
            assignments[best_track.id] = best_track.center
        return assignments

