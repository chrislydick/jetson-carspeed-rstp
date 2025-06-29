#!/usr/bin/env python3
"""Interactive homography calibration tool."""

from __future__ import annotations

import argparse
import json
import logging
from typing import List

import cv2

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate homography from four points"
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--image", help="Path to input image")
    src.add_argument("--rtsp", help="RTSP URL to grab a frame")
    parser.add_argument(
        "--width", type=float, required=True, help="Real-world lane width in meters"
    )
    parser.add_argument(
        "--length", type=float, required=True, help="Real-world lane length in meters"
    )
    parser.add_argument(
        "--output", default="homography.json", help="Output JSON file for matrix"
    )
    return parser.parse_args()


class PointCollector:
    def __init__(self, frame):
        self.frame = frame
        self.view = frame.copy()
        self.points: List[List[int]] = []

    def callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(self.points) < 4:
            self.points.append([x, y])
            cv2.circle(self.view, (x, y), 5, (0, 0, 255), -1)
            cv2.imshow("frame", self.view)


def collect_points(frame) -> List[List[int]]:
    collector = PointCollector(frame)
    cv2.imshow("frame", frame)
    cv2.setMouseCallback("frame", collector.callback)
    while len(collector.points) < 4:
        if cv2.waitKey(10) == 27:  # ESC to cancel
            break
    cv2.destroyAllWindows()
    return collector.points


def main() -> None:
    args = parse_args()
    logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)
    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            raise FileNotFoundError(args.image)
    else:
        cap = cv2.VideoCapture(args.rtsp)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError("Failed to grab frame from RTSP")

    pts = collect_points(frame)
    if len(pts) != 4:
        logger.error("Need four points to compute homography")

        return

    src_pts = cv2.float32(pts)
    dst_pts = cv2.float32(
        [
            [0, 0],
            [args.width, 0],
            [args.width, args.length],
            [0, args.length],
        ]
    )
    H, _ = cv2.findHomography(src_pts, dst_pts)
    if H is None:
        raise RuntimeError("Could not compute homography")
    data = [[float(v) for v in row] for row in H]
    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Saved homography to %s", args.output)
