import argparse
import cv2

from speed_detector import run_capture, load_homography


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RTSP vehicle speed detector")
    parser.add_argument("--rtsp", required=True, help="RTSP stream URL")
    parser.add_argument("--model", required=True, help="Path to YOLO model")
    parser.add_argument("--db", default="vehicles.db", help="Output SQLite DB path")
    parser.add_argument("--ppm", type=float, required=True, help="Pixels per meter scale")
    parser.add_argument("--iou-threshold", type=float, default=0.3, help="Detection IoU threshold")
    parser.add_argument("--decay-time", type=float, default=1.0, help="Seconds to keep lost tracks")
    parser.add_argument("--homography", help="Path to 3x3 homography JSON/YAML")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.rtsp)
    H = load_homography(args.homography) if args.homography else None
    run_capture(cap, args.model, args.db, args.ppm, args.iou_threshold, args.decay_time, H)
