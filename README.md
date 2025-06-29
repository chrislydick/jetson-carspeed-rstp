# Jetson Car Speed DeepStream

This repository demonstrates a DeepStream pipeline for measuring vehicle speed from RTSP streams or local H.265 MP4 files. A custom GStreamer plug-in reads tracker metadata and logs speed estimates to a SQLite database.

## Prerequisites

* NVIDIA DeepStream SDK 6 or newer with GStreamer
* Python 3.8+
* GObject introspection bindings (PyGObject)
* SQLite development libraries for building the plug-in
* `libgstreamer1.0-dev` and `libgstreamer-plugins-base1.0-dev` to compile the plug-in

## Installation

```bash
pip install -e .
```


## Building the speed plug-in

Run `make` to build `libspeedtrack.so`. If the NVIDIA DeepStream headers are
installed, pass `USE_DEEPSTREAM=1` to enable full functionality. The compiled
library must be on `GST_PLUGIN_PATH` for GStreamer to load it:

```bash
make [USE_DEEPSTREAM=1]
export GST_PLUGIN_PATH=$PWD:$GST_PLUGIN_PATH
```

## Running the pipeline

Use the `carspeed` CLI (installed via `pip install -e .`) to build a DeepStream pipeline using hardware decode, `nvinfer`, `nvtracker`, and the custom `speedtrack` element.

### RTSP example
```bash
carspeed --rtsp rtsp://camera/stream \
  --config ds_config.txt --db vehicles.db --ppm 20 \
  --engine /path/to/trafficcamnet.trt
```

### H.265 MP4 example
```bash
carspeed --video sample.mp4 \
  --config ds_config.txt --db test.db --ppm 20 \
  --engine /path/to/trafficcamnet.trt
```
Scripts `deepstream_speed.py` and `carspeed.py` are kept for backward compatibility and simply invoke this CLI.


## Calibrating the homography

The helper script `calibrate_homography.py` can generate the transformation
matrix for your camera view. Logging output follows the Python logging level:

```bash
# grab a frame from an RTSP stream
python calibrate_homography.py --rtsp rtsp://camera/stream \
  --width 3.5 --length 20

# or load an existing image
python calibrate_homography.py --image frame.jpg \
  --width 3.5 --length 20
```

Click the four lane corners starting from the near left and proceeding clockwise
(left-front, right-front, right-rear, left-rear). The script saves
`homography.json`, which can be supplied to `deepstream_speed.py` via
`--homography`.
The script outputs progress using Python's `logging` module and honours
the `--log-level` setting.

## nvinfer configuration

`ds_config.txt` does not include an engine file. Download the pre-built TrafficCamNet engine from NGC or create one with the TAO converter, then provide its path via `--engine`. Use this option as well if you retrain a detector and build a new `.trt` file.

## Retraining with NVIDIA TAO

To train your own detector (for example a YOLOv9 model) install the NVIDIA TAO Toolkit and run the training commands inside its Docker container. After training:

1. Export the model to ONNX using `tao export`.
2. Convert the ONNX file to TensorRT with `tao-converter` to produce `your_model.trt`.
3. Run `deepstream_speed.py --engine your_model.trt` to use the new network.

## Database schema

The plug-in writes rows to the `vehicles` table containing:

- `timestamp` – capture time in seconds
- `track_id` – object tracking ID
- `speed` – estimated speed in meters per second

Use standard SQLite tools to analyse the results.

## Standalone Python tracker

The helper scripts `carspeed.py` and `carspeed_file.py` provide a lightweight
pipeline using a simple ByteTrack implementation. The tracker behaviour can be
configured with:

* `--iou-threshold` – IoU required to associate a detection with an existing
  track (default `0.3`).
* `--decay-time` – time in seconds to keep a track alive when detections are
  missing (default `1.0`).

These scripts are useful for quick experiments without a full DeepStream setup.

## Development

Run the unit tests with `pytest -q`:

```bash
pytest -q
```

Some tests rely on GStreamer and DeepStream. If these dependencies are not
available, they will be skipped.

### Docker

A `Dockerfile` is included for reproducible JetPack 6.0 builds. Build and run:

```bash
docker build -t carspeed .
docker run --runtime nvidia -it carspeed
```

Continuous integration executes `pytest` and a static analysis pass with
`clang --analyze speed_plugin.c $(pkg-config --cflags --libs gstreamer-1.0 gstreamer-base-1.0)`
on every pull request.
