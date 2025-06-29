#!/usr/bin/env python3
"""DeepStream-based car speed detection pipeline."""
import argparse
import json
import logging
logger = logging.getLogger(__name__)

import gi

try:
    import yaml
except Exception:  # pragma: no cover - PyYAML may be missing
    yaml = None


gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)


def load_homography(path: str):
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


def build_pipeline(
    uri: str,
    config: str,
    engine: str,
    db: str,
    ppm: float,
    is_rtsp: bool,
    homography=None,
    window: int = 3,
    batch_size: int = 1,
    width: int = 1280,
    height: int = 720,
) -> Gst.Pipeline:
    if is_rtsp:
        src = f"rtspsrc location={uri} latency=100 ! rtph265depay ! h265parse ! nvv4l2decoder"
    else:
        src = f"filesrc location={uri} ! qtdemux ! h265parse ! nvv4l2decoder"

    homography_str = (
        " " + "homography=" + ",".join(str(v) for v in homography)
        if homography
        else ""
    )
    pipe_desc = (
        f"{src} ! nvstreammux name=mux batch-size={batch_size} "
        f"width={width} height={height} nvbuf-memory-type=0 ! "
        f"nvinfer config-file-path={config} ! nvtracker ! "
        f"speedtrack ppm={ppm} db={db} window={window}{homography_str} ! "
        f"fakesink sync=false"
    )
    return Gst.parse_launch(pipe_desc)


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepStream speed detector")
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--rtsp", help="RTSP stream URL")
    src_group.add_argument("--video", help="Path to H.265 MP4 file")
    parser.add_argument("--config", default="ds_config.txt", help="nvinfer config file")
    parser.add_argument("--engine", default="trafficcamnet.trt", help="TensorRT engine (.trt)")
    parser.add_argument("--db", default="vehicles.db", help="SQLite DB path")
    parser.add_argument("--ppm", type=float, required=True, help="Pixels per meter")
    parser.add_argument("--homography", help="Path to 3x3 homography JSON/YAML")
    parser.add_argument("--window", type=int, default=3, help="History window size")
    parser.add_argument("--batch-size", type=int, default=1, help="nvstreammux batch size")
    parser.add_argument("--resize", help="Resize as WIDTHxHEIGHT for nvstreammux")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()
    logging.basicConfig(format="%(levelname)s:%(message)s",
                        level=getattr(logging, args.log_level.upper(), logging.INFO))
    if not args.engine.endswith(".trt"):
        parser.error("--engine must specify a .trt file")

    uri = args.rtsp if args.rtsp else args.video
    H = load_homography(args.homography) if args.homography else None
    width, height = 1280, 720
    if args.resize:
        if "x" not in args.resize:
            raise ValueError("--resize must be WIDTHxHEIGHT")
        w, h = args.resize.split("x", 1)
        width, height = int(w), int(h)

    pipeline = build_pipeline(
        uri,
        args.config,
        args.engine,
        args.db,
        args.ppm,
        args.rtsp is not None,
        H,
        args.window,
        args.batch_size,
        width,
        height,
    )
    bus = pipeline.get_bus()
    pipeline.set_state(Gst.State.PLAYING)
    logger.info("Pipeline started")

    try:
        while True:
            msg = bus.timed_pop_filtered(
                100 * Gst.MSECOND, Gst.MessageType.ERROR | Gst.MessageType.EOS
            )
            if msg:
                break
    except KeyboardInterrupt:
        pass

    pipeline.set_state(Gst.State.NULL)
    logger.info("Pipeline stopped")


if __name__ == "__main__":
    main()
