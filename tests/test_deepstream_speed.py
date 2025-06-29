import sys
import os
import types
import pytest

# Add project root to path and stub gi
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
if "gi" not in sys.modules:
    gi_stub = types.ModuleType("gi")
    repo = types.ModuleType("gi.repository")
    repo.Gst = types.SimpleNamespace(init=lambda *a, **kw: None, Pipeline=object)
    repo.GLib = types.SimpleNamespace()
    gi_stub.require_version = lambda *a, **kw: None
    gi_stub.repository = repo
    sys.modules["gi"] = gi_stub
    sys.modules["gi.repository"] = repo

from carspeed import cli as deepstream_speed
from carspeed.pipeline import deepstream_graph


def test_engine_suffix_required(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--video", "v.mp4", "--ppm", "1", "--engine", "bad.engine"],
    )
    with pytest.raises(SystemExit):
        deepstream_speed.main()


def test_engine_passed_to_pipeline(monkeypatch):
    captured = {}

    class DummyGst:
        class State:
            PLAYING = 0
            NULL = 1

        class MessageType:
            ERROR = 1
            EOS = 2

        MSECOND = 1

    def fake_build_pipeline(opts, *a, **kw):
        captured["engine"] = opts.engine

        class DummyBus:
            def timed_pop_filtered(self, *args, **kwargs):
                return True

        class DummyPipeline:
            def get_bus(self):
                return DummyBus()

            def set_state(self, state):
                pass

        return DummyPipeline()

    monkeypatch.setattr(deepstream_graph, "build_pipeline", fake_build_pipeline)
    repo = sys.modules.get("gi.repository")
    if repo:
        monkeypatch.setattr(repo, "Gst", DummyGst, raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--video",
            "v.mp4",
            "--ppm",
            "1",
            "--engine",
            "model.trt",
        ],
    )

    deepstream_speed.main()
    assert captured["engine"] == "model.trt"
