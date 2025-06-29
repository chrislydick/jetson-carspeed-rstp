import json
from pathlib import Path

from carspeed.core.speed_math import rolling_speed


ASSET = Path(__file__).parent / "assets" / "synthetic_centroids.json"


def test_mean_speed_kmh():
    data = json.loads(ASSET.read_text())
    centroids = [tuple(map(float, c)) for c in data["centroids"]]
    timestamps = [float(t) for t in data["timestamps"]]
    speeds = rolling_speed(centroids, timestamps, ppm=20, window=3)
    if not speeds:
        raise AssertionError("no speeds computed")
    mean_kmh = sum(speeds) / len(speeds) * 3.6
    assert 54 <= mean_kmh <= 55
