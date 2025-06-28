#!/usr/bin/env python3
"""DeepStream-based car speed detection pipeline."""
import argparse
import json
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
    db: str,
    ppm: float,
    is_rtsp: bool,
    homography=None,
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
        f"{src} ! nvstreammux name=mux batch-size=1 width=1280 height=720 ! "
        f"nvinfer config-file-path={config} ! nvtracker ! "
        f"speedtrack ppm={ppm} db={db}{homography_str} ! fakesink sync=false"
    )
    return Gst.parse_launch(pipe_desc)


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepStream speed detector")
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--rtsp", help="RTSP stream URL")
    src_group.add_argument("--video", help="Path to H.265 MP4 file")
    parser.add_argument("--config", default="ds_config.txt", help="nvinfer config file")
    parser.add_argument("--db", default="vehicles.db", help="SQLite DB path")
    parser.add_argument("--ppm", type=float, required=True, help="Pixels per meter")
    parser.add_argument("--homography", help="Path to 3x3 homography JSON/YAML")
    args = parser.parse_args()

    uri = args.rtsp if args.rtsp else args.video
    H = load_homography(args.homography) if args.homography else None
    pipeline = build_pipeline(uri, args.config, args.db, args.ppm, args.rtsp is not None, H)
    bus = pipeline.get_bus()
    pipeline.set_state(Gst.State.PLAYING)

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


if __name__ == "__main__":
    main()
