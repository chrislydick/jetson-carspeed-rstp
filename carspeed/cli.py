# -*- coding: utf-8 -*-
"""Command line interface for speed detection."""

import argparse
from gi.repository import Gst

from .pipelines.deepstream import build_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepStream speed detector")
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--rtsp", help="RTSP stream URL")
    src_group.add_argument("--video", help="Path to H.265 MP4 file")
    parser.add_argument("--config", default="ds_config.txt", help="nvinfer config file")
    parser.add_argument("--db", default="vehicles.db", help="SQLite DB path")
    parser.add_argument("--ppm", type=float, required=True, help="Pixels per meter")
    args = parser.parse_args()

    uri = args.rtsp if args.rtsp else args.video
    pipeline = build_pipeline(
        uri, args.config, args.db, args.ppm, args.rtsp is not None
    )
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
