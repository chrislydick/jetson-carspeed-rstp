"""SQLite helper functions."""

from __future__ import annotations

import sqlite3


def init_db(path: str) -> sqlite3.Connection:
    """Create the vehicles table if needed and return a connection."""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL,
        track_id INTEGER,
        label TEXT,
        speed REAL,
        x1 INTEGER, y1 INTEGER, x2 INTEGER, y2 INTEGER,
        confidence REAL
    )"""
    )
    conn.commit()
    return conn
