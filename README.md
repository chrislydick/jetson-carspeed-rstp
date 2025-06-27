# Jetson Car Speed RTSP

This repository contains a simple example for detecting vehicles from an RTSP stream and logging their estimated speed to a SQLite database. It is intended for NVIDIA Jetson devices but should run on any Linux system with Python.

## Prerequisites

* Python 3.8+
* [OpenCV](https://pypi.org/project/opencv-python/)
* [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)

Install dependencies with:

```bash
pip install opencv-python ultralytics
```

Download a YOLO model (e.g., `yolov8n.pt`) from the Ultralytics project or train your own.

## Usage

Run the RTSP example and pass your stream URL, YOLO model path, the desired output database path, and the pixel-per-meter (PPM) scale for your camera setup:

```bash
python carspeed.py --rtsp rtsp://camera/stream --model yolov8n.pt --db vehicles.db --ppm 20
```

The script will connect to the RTSP stream, detect vehicles in each frame, estimate their speed based on tracked pixel movement, and write the results to an SQLite database called `vehicles.db` by default.

### Testing with an H.265 MP4 file

You can also run the speed detection against a local MP4 file encoded with UniFi's H.265 format. Use the `carspeed_file.py` helper:

```bash
python carspeed_file.py --video example.mp4 --model yolov8n.pt --db test.db --ppm 20
```

Make sure your OpenCV build has H.265 support through FFmpeg so the file can be decoded correctly.

The PPM value represents how many pixels correspond to one meter in the scene and must be measured for your specific camera angle.

## Database schema

The `vehicles` table contains:

- `timestamp`: capture time in seconds
- `track_id`: ID assigned to a tracked vehicle
- `label`: predicted object class
- `speed`: estimated speed in meters per second
- `x1`, `y1`, `x2`, `y2`: bounding box coordinates
- `confidence`: YOLO confidence score

You can query this SQLite database from other programs to analyze vehicle speeds and counts.
