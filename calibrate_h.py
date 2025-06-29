#!/usr/bin/env python3
"""GUI tool for camera-to-world homography calibration."""

from __future__ import annotations

import argparse
import json
from typing import List

import cv2
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets


Point = List[int]


def load_frame(video: str | None, rtsp: str | None) -> np.ndarray:
    src = video or rtsp
    cap = cv2.VideoCapture(src)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError(f"Failed to capture frame from {src}")
    return frame


def qpixmap_from_cv(image: np.ndarray) -> QtGui.QPixmap:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    bytes_per_line = ch * w
    qimage = QtGui.QImage(
        rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888
    )
    return QtGui.QPixmap.fromImage(qimage)


class ImageWidget(QtWidgets.QLabel):
    def __init__(self, pixmap: QtGui.QPixmap, callback):
        super().__init__()
        self.base = pixmap
        self.setPixmap(self.base)
        self.points: List[Point] = []
        self.callback = callback

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if len(self.points) >= 4:
            return
        pos = event.position() if hasattr(event, "position") else event.posF()
        x = int(pos.x())
        y = int(pos.y())
        self.points.append([x, y])
        pix = QtGui.QPixmap(self.pixmap())
        painter = QtGui.QPainter(pix)
        pen = QtGui.QPen(QtCore.Qt.red)
        pen.setWidth(5)
        painter.setPen(pen)
        painter.drawEllipse(QtCore.QPointF(x, y), 5, 5)
        painter.end()
        self.setPixmap(pix)
        if len(self.points) == 4:
            self.callback(self.points)


class Calibrator(QtWidgets.QMainWindow):
    def __init__(self, frame: np.ndarray):
        super().__init__()
        self.setWindowTitle("Homography Calibrator")
        self.image = frame
        pix = qpixmap_from_cv(frame)
        self.widget = ImageWidget(pix, self.collect_world_points)
        self.setCentralWidget(self.widget)
        self.show()

    def collect_world_points(self, img_pts: List[Point]) -> None:
        labels = ["BL", "BR", "TR", "TL"]
        world_pts: List[Point] = []
        for lbl in labels:
            while True:
                text, ok = QtWidgets.QInputDialog.getText(
                    self,
                    "World coordinates",
                    f"{lbl} X,Y in meters:",
                )
                if not ok:
                    return
                try:
                    x_str, y_str = text.split(",")
                    world_pts.append([float(x_str), float(y_str)])
                    break
                except ValueError:
                    QtWidgets.QMessageBox.warning(
                        self, "Invalid", "Enter values as X,Y"
                    )
        self.compute_and_save(img_pts, world_pts)

    def compute_and_save(self, img: List[Point], world: List[Point]) -> None:
        src = np.float32(img)
        dst = np.float32(world)
        H, _ = cv2.findHomography(src, dst)
        if H is None:
            QtWidgets.QMessageBox.warning(self, "Error", "Could not compute homography")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save JSON", "homography.json", "JSON Files (*.json)"
        )
        if not path:
            return
        data = {
            "image_points": img,
            "world_points": world,
            "H": H.tolist(),
        }
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)
        QtWidgets.QMessageBox.information(self, "Saved", f"Saved to {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Homography calibration GUI")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="Path to video file")
    src.add_argument("--rtsp", help="RTSP URL")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = load_frame(args.video, args.rtsp)
    app = QtWidgets.QApplication([])
    _ = Calibrator(frame)
    app.exec()


if __name__ == "__main__":
    main()
