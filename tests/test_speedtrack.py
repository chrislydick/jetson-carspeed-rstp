import sqlite3
import pytest

try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
except Exception:  # pragma: no cover - skip if gi/Gst missing
    Gst = None

try:
    import pyds
except Exception:  # pragma: no cover - skip if pyds missing
    pyds = None


@pytest.mark.skipif(Gst is None or pyds is None, reason="GStreamer or DeepStream not available")
def test_speedtrack_writes_rows(tmp_path):
    Gst.init(None)
    db_path = tmp_path / "vehicles.db"
    pipe_desc = f"appsrc name=src ! speedtrack ppm=1 db={db_path} ! fakesink sync=false"
    pipeline = Gst.parse_launch(pipe_desc)
    appsrc = pipeline.get_by_name("src")
    pipeline.set_state(Gst.State.PLAYING)

    def _push(buf, ts_ns, y):
        batch_meta = pyds.gst_buffer_add_nvds_batch_meta(buf, 1)
        frame_meta = pyds.nvds_add_frame_meta_to_batch(batch_meta, pyds.alloc_nvds_frame_meta())
        frame_meta.ntp_timestamp = ts_ns
        obj_meta = pyds.nvds_acquire_obj_meta_from_pool(batch_meta)
        obj_meta.object_id = 1
        obj_meta.rect_params.left = 0
        obj_meta.rect_params.top = y
        obj_meta.rect_params.width = 10
        obj_meta.rect_params.height = 10
        pyds.nvds_add_obj_meta_to_frame(frame_meta, obj_meta, None)
        appsrc.emit("push-buffer", buf)

    buf1 = Gst.Buffer.new()
    _push(buf1, 0, 0)
    buf2 = Gst.Buffer.new()
    _push(buf2, int(1e9), 20)

    appsrc.emit("end-of-stream")
    bus = pipeline.get_bus()
    while True:
        msg = bus.timed_pop_filtered(100 * Gst.MSECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
        if msg:
            break

    pipeline.set_state(Gst.State.NULL)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM vehicles")
        count = cur.fetchone()[0]
    finally:
        conn.close()
    assert count > 0


@pytest.mark.skipif(Gst is None or pyds is None, reason="GStreamer or DeepStream not available")
def test_speedtrack_smoothing(tmp_path):
    Gst.init(None)
    db_path = tmp_path / "vehicles.db"
    pipe_desc = (
        f"appsrc name=src ! speedtrack ppm=1 window=3 db={db_path} ! fakesink sync=false"
    )
    pipeline = Gst.parse_launch(pipe_desc)
    appsrc = pipeline.get_by_name("src")
    pipeline.set_state(Gst.State.PLAYING)

    def _push(buf, ts_ns, y):
        batch_meta = pyds.gst_buffer_add_nvds_batch_meta(buf, 1)
        frame_meta = pyds.nvds_add_frame_meta_to_batch(batch_meta, pyds.alloc_nvds_frame_meta())
        frame_meta.ntp_timestamp = ts_ns
        obj_meta = pyds.nvds_acquire_obj_meta_from_pool(batch_meta)
        obj_meta.object_id = 1
        obj_meta.rect_params.left = 0
        obj_meta.rect_params.top = y
        obj_meta.rect_params.width = 10
        obj_meta.rect_params.height = 10
        pyds.nvds_add_obj_meta_to_frame(frame_meta, obj_meta, None)
        appsrc.emit("push-buffer", buf)

    _push(Gst.Buffer.new(), 0, 0)
    _push(Gst.Buffer.new(), int(1e9), 21)
    _push(Gst.Buffer.new(), int(2e9), 39)

    appsrc.emit("end-of-stream")
    bus = pipeline.get_bus()
    while True:
        msg = bus.timed_pop_filtered(
            100 * Gst.MSECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR
        )
        if msg:
            break

    pipeline.set_state(Gst.State.NULL)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT speed FROM vehicles ORDER BY timestamp")
        rows = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()
    assert len(rows) == 2
    assert rows[1] == pytest.approx(19.5, rel=0.1)
