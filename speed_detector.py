import sqlite3
import time
from typing import List, Tuple, Optional
import json

try:
    import yaml
except Exception:  # pragma: no cover - PyYAML may be missing
    yaml = None

import cv2
from ultralytics import YOLO


class VehicleTrack:
    def __init__(self, center: Tuple[float, float], ts: float):
        self.center = center
        self.last_ts = ts


class SimpleTracker:
    def __init__(self, max_distance: float = 50):
        self.tracks = {}
        self.next_id = 0
        self.max_distance = max_distance

    def update(self, detections: List[Tuple[int, int, int, int]], ts: float):
        matches = {}
        for box in detections:
            cx = (box[0] + box[2]) / 2
            cy = (box[1] + box[3]) / 2
            matched_id = None
            for tid, track in self.tracks.items():
                dist = ((cx - track.center[0]) ** 2 + (cy - track.center[1]) ** 2) ** 0.5
                if dist < self.max_distance:
                    matched_id = tid
                    break
            if matched_id is None:
                matched_id = self.next_id
                self.next_id += 1
            self.tracks[matched_id] = VehicleTrack((cx, cy), ts)
            matches[matched_id] = (cx, cy)
        return matches


def load_homography(path: str) -> Optional[List[float]]:
    if not path:
        return None
    with open(path, "r") as f:
        if yaml and path.endswith((".yml", ".yaml")):
            data = yaml.safe_load(f)
        else:
            data = json.load(f)
    flat = [float(v) for row in data for v in row]
    if len(flat) != 9:
        raise ValueError("homography must have 9 values")
    return flat


def init_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL,
        track_id INTEGER,
        label TEXT,
        speed REAL,
        x1 INTEGER, y1 INTEGER, x2 INTEGER, y2 INTEGER,
        confidence REAL
    )"""
    )
    conn.commit()
    return conn


def run_capture(
    cap: cv2.VideoCapture,
    model_path: str,
    db_path: str,
    ppm: float,
    max_distance: float = 50,
    homography: Optional[List[float]] = None,
):
    model = YOLO(model_path)
    conn = init_db(db_path)
    tracker = SimpleTracker(max_distance)
    prev_positions = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        ts = time.time()
        detections = []
        results = model(frame)
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                if cls not in [2, 5, 7]:
                    continue  # vehicle classes
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append((x1, y1, x2, y2, float(box.conf[0]), r.names[cls]))
        boxes = [d[:4] for d in detections]
        assignments = tracker.update(boxes, ts)
        for (x1, y1, x2, y2, conf, label), (track_id, center) in zip(detections, assignments.items()):
            cx, cy = center
            if homography:
                tx = homography[0] * cx + homography[1] * cy + homography[2]
                ty = homography[3] * cx + homography[4] * cy + homography[5]
                tz = homography[6] * cx + homography[7] * cy + homography[8]
                if tz != 0:
                    cx = tx / tz
                    cy = ty / tz
            speed = 0.0
            if track_id in prev_positions:
                px, py, pts = prev_positions[track_id]
                dist_pix = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                dist_m = dist_pix / ppm
                dt = ts - pts
                if dt > 0:
                    speed = dist_m / dt  # m/s
            prev_positions[track_id] = (cx, cy, ts)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO vehicles(timestamp, track_id, label, speed, x1, y1, x2, y2, confidence)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ts, track_id, label, speed, x1, y1, x2, y2, conf),
            )
            conn.commit()

    cap.release()
    conn.close()
