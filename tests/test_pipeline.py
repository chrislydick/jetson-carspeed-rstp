# -*- coding: utf-8 -*-
import pytest

try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    GST_AVAILABLE = True
    Gst.init(None)
except Exception:
    GST_AVAILABLE = False
    Gst = None


@pytest.mark.skipif(not GST_AVAILABLE, reason="GStreamer not available")
def test_build_pipeline():
    from deepstream_speed import build_pipeline

    pipeline = build_pipeline("sample.mp4", "ds_config.txt", "test.db", 20.0, False)
    assert isinstance(pipeline, Gst.Pipeline)
