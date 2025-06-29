"""Command line interface for carspeed."""

from __future__ import annotations

import argparse
import logging
from typing import Iterable, Optional


logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    """Return the argument parser."""
    parser = argparse.ArgumentParser(description="DeepStream speed detector")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--rtsp", help="RTSP stream URL")
    src.add_argument("--video", help="Path to H.265 MP4 file")
    parser.add_argument("--config", default="ds_config.txt", help="nvinfer config file")
    parser.add_argument(
        "--engine", default="trafficcamnet.trt", help="TensorRT engine (.trt)"
    )
    parser.add_argument("--db", default="vehicles.db", help="SQLite DB path")
    parser.add_argument("--ppm", type=float, required=True, help="Pixels per meter")
    parser.add_argument("--homography", help="Path to 3x3 homography JSON/YAML")
    parser.add_argument("--window", type=int, default=3, help="History window size")
    parser.add_argument(
        "--batch-size", type=int, default=1, help="nvstreammux batch size"
    )
    parser.add_argument("--resize", help="Resize as WIDTHxHEIGHT for nvstreammux")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> None:
    """Parse arguments and run the pipeline."""
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        format="%(levelname)s:%(message)s",
        level=getattr(logging, args.log_level.upper(), logging.INFO),
    )

    if not args.engine.endswith(".trt"):
        parser.error("--engine must specify a .trt file")

    width, height = 1280, 720
    if args.resize:
        if "x" not in args.resize:
            parser.error("--resize must be WIDTHxHEIGHT")
        w, h = args.resize.split("x", 1)
        width, height = int(w), int(h)

    from gi.repository import Gst  # imported after argument parsing
    from .pipeline.config import PipelineOptions
    from .pipeline.deepstream_graph import build_pipeline

    opts = PipelineOptions(
        uri=args.rtsp if args.rtsp else args.video,
        config=args.config,
        engine=args.engine,
        db=args.db,
        ppm=args.ppm,
        is_rtsp=args.rtsp is not None,
        homography=None if args.homography is None else args.homography,
        window=args.window,
        batch_size=args.batch_size,
        width=width,
        height=height,
    )

    pipeline = build_pipeline(opts)
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


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
