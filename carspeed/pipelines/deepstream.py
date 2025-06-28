# -*- coding: utf-8 -*-
"""DeepStream pipeline builders."""

from gi.repository import Gst

Gst.init(None)


def build_pipeline(
    uri: str, config: str, db: str, ppm: float, is_rtsp: bool
) -> Gst.Pipeline:
    """Return a GStreamer pipeline for speed estimation."""
    if is_rtsp:
        src = f"rtspsrc location={uri} latency=100 ! rtph265depay ! h265parse ! nvv4l2decoder"
    else:
        src = f"filesrc location={uri} ! qtdemux ! h265parse ! nvv4l2decoder"

    pipe_desc = (
        f"{src} ! nvstreammux name=mux batch-size=1 width=1280 height=720 ! "
        f"nvinfer config-file-path={config} ! nvtracker ! "
        f"speedtrack ppm={ppm} db={db} ! fakesink sync=false"
    )
    return Gst.parse_launch(pipe_desc)
