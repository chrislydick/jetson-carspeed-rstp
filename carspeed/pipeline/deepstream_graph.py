"""Create DeepStream pipelines."""

from __future__ import annotations

from gi.repository import Gst

from .config import PipelineOptions


Gst.init(None)


def build_pipeline(opts: PipelineOptions) -> Gst.Pipeline:
    """Return a ``Gst.Pipeline`` for the given options."""
    src = (
        f"rtspsrc location={opts.uri} latency=100 ! "
        "rtph265depay ! h265parse ! nvv4l2decoder"
        if opts.is_rtsp
        else f"filesrc location={opts.uri} ! qtdemux ! h265parse ! nvv4l2decoder"
    )

    homography = (
        " " + "homography=" + opts.homography if opts.homography is not None else ""
    )
    pipe_desc = (
        f"{src} ! nvstreammux name=mux batch-size={opts.batch_size} "
        f"width={opts.width} height={opts.height} nvbuf-memory-type=0 ! "
        f"nvinfer config-file-path={opts.config} ! nvtracker ! "
        f"speedtrack ppm={opts.ppm} db={opts.db} window={opts.window}{homography} ! "
        "fakesink sync=false"
    )
    return Gst.parse_launch(pipe_desc)
