# Jetson Car Speed DeepStream

This repository demonstrates a DeepStream pipeline for measuring vehicle speed from RTSP streams or local H.265 MP4 files. A custom GStreamer plug-in reads tracker metadata and logs speed estimates to a SQLite database.

## Prerequisites

The examples were developed on a Jetson AGX Orin (64 GB) running JetPack 5.
Ensure that your system has the following components installed:

* NVIDIA DeepStream SDK 6 or newer with GStreamer
* Jetson Linux with the matching GPU drivers from JetPack
* Python 3.8+
* GObject introspection bindings (PyGObject)
* SQLite development libraries for building the plug-in

## Building the speed plug-in

Run `make` to compile `speed_plugin.c` into `libspeedtrack.so` and update your `GST_PLUGIN_PATH` so GStreamer can discover it:

```bash
make
export GST_PLUGIN_PATH=$PWD:$GST_PLUGIN_PATH
```

## Running the pipeline

The `deepstream_speed.py` helper builds a simple pipeline using hardware decode, `nvinfer`, `nvtracker`, and the custom `speedtrack` element.

### RTSP example

```bash
python deepstream_speed.py --rtsp rtsp://camera/stream \
  --config ds_config.txt --db vehicles.db --ppm 20
```

### H.265 MP4 example

```bash
python deepstream_speed.py --video sample.mp4 \
  --config ds_config.txt --db test.db --ppm 20
```

`--ppm` is the pixel-per-meter scale for your camera view. Speeds are written to the SQLite database specified with `--db`.

## nvinfer configuration

`ds_config.txt` is a minimal configuration for an INT8 TensorRT-optimized YOLOv8l engine. Replace `model-engine-file` with your preferred engine if needed.

## Database schema

The plug-in writes rows to the `vehicles` table containing:

- `timestamp` – capture time in seconds
- `track_id` – object tracking ID
- `speed` – estimated speed in meters per second

Use standard SQLite tools to analyse the results.
