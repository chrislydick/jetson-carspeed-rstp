import sys
import os
import types
import pytest
import json

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


def test_engine_passed_to_pipeline(monkeypatch, tmp_path):
    captured = {}
    config = tmp_path / "ds_config.txt"
    config.write_text("[property]\nmodel-engine-file=\nbatch-size=1\n")

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
        captured["config"] = opts.config

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
            "--config",
            str(config),
            "--engine",
            "model.trt",
        ],
    )

    deepstream_speed.main()
    assert captured["engine"] == "model.trt"
    assert (
        "model-engine-file=model.trt"
        in open(captured["config"], encoding="utf-8").read()
    )


def test_load_homography_flattens_json(tmp_path):
    homography = tmp_path / "homography.json"
    homography.write_text(json.dumps([[1, 0, 2], [0, 1, 3], [0, 0, 1]]))

    assert (
        deepstream_speed.load_homography(str(homography))
        == "1.0,0.0,2.0,0.0,1.0,3.0,0.0,0.0,1.0"
    )


def test_load_homography_rejects_wrong_shape(tmp_path):
    homography = tmp_path / "bad.json"
    homography.write_text(json.dumps([[1, 0], [0, 1]]))

    with pytest.raises(ValueError, match="9 values"):
        deepstream_speed.load_homography(str(homography))


def test_write_engine_config_inserts_missing_property(tmp_path):
    config = tmp_path / "config.txt"
    config.write_text("[property]\nbatch-size=1\n")

    generated = deepstream_speed.write_engine_config(str(config), "custom.trt")

    assert "model-engine-file=custom.trt" in open(generated, encoding="utf-8").read()
