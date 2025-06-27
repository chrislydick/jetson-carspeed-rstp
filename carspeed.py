import argparse
import cv2

from speed_detector import run_capture


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RTSP vehicle speed detector")
    parser.add_argument("--rtsp", required=True, help="RTSP stream URL")
    parser.add_argument("--model", required=True, help="Path to YOLO model")
    parser.add_argument("--db", default="vehicles.db", help="Output SQLite DB path")
    parser.add_argument("--ppm", type=float, required=True, help="Pixels per meter scale")
    parser.add_argument("--max-distance", type=float, default=50, help="Max pixel distance for tracking")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.rtsp)
    run_capture(cap, args.model, args.db, args.ppm, args.max_distance)
