"""Command line interface for carspeed."""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
from pathlib import Path
from typing import Iterable, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is optional
    yaml = None


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


def load_homography(path: str) -> str:
    """Return a 3x3 homography file as a comma-separated matrix string."""
    with open(path, "r", encoding="utf-8") as fh:
        if Path(path).suffix.lower() in {".yml", ".yaml"}:
            if yaml is None:
                raise RuntimeError("PyYAML is required to read YAML homography files")
            data = yaml.safe_load(fh)
        else:
            data = json.load(fh)

    if isinstance(data, dict):
        data = data.get("homography") or data.get("matrix") or data.get("H")
    if data is None:
        raise ValueError("homography file must contain a 3x3 matrix")

    flat = []
    for row in data:
        if isinstance(row, (list, tuple)):
            flat.extend(row)
        else:
            flat.append(row)
    if len(flat) != 9:
        raise ValueError("homography must have 9 values")
    return ",".join(str(float(value)) for value in flat)


def write_engine_config(config_path: str, engine_path: str) -> str:
    """Copy an nvinfer config and set its model-engine-file entry."""
    source = Path(config_path)
    lines = source.read_text(encoding="utf-8").splitlines()
    output = []
    replaced = False
    in_property = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_property = stripped == "[property]"
        if in_property and stripped.startswith("model-engine-file="):
            output.append(f"model-engine-file={engine_path}")
            replaced = True
        else:
            output.append(line)

    if not replaced:
        insert_at = 0
        for idx, line in enumerate(output):
            if line.strip() == "[property]":
                insert_at = idx + 1
                break
        output.insert(insert_at, f"model-engine-file={engine_path}")

    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", prefix="carspeed-nvinfer-", delete=False, encoding="utf-8"
    ) as fh:
        fh.write("\n".join(output) + "\n")
        return fh.name


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

    config = write_engine_config(args.config, args.engine)
    homography = None if args.homography is None else load_homography(args.homography)

    from gi.repository import Gst  # imported after argument parsing
    from .pipeline.config import PipelineOptions
    from .pipeline.deepstream_graph import build_pipeline

    opts = PipelineOptions(
        uri=args.rtsp if args.rtsp else args.video,
        config=config,
        engine=args.engine,
        db=args.db,
        ppm=args.ppm,
        is_rtsp=args.rtsp is not None,
        homography=homography,
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
