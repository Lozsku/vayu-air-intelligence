"""SQLite time-series store for air-quality measurements.

Schema mirrors the shape of any civic time-series (station × pollutant × time),
which is exactly why the same engine that powered our real-time markets platform
transfers directly to community sensing.
"""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS stations (
    id       TEXT PRIMARY KEY,
    city     TEXT NOT NULL,
    name     TEXT NOT NULL,
    country  TEXT,
    lat      REAL,
    lon      REAL
);
CREATE TABLE IF NOT EXISTS measurements (
    station_id TEXT NOT NULL,
    ts         INTEGER NOT NULL,          -- epoch seconds, top of hour
    pollutant  TEXT NOT NULL,
    value      REAL NOT NULL,
    PRIMARY KEY (station_id, pollutant, ts)
);
CREATE INDEX IF NOT EXISTS idx_meas_lookup ON measurements (station_id, pollutant, ts);
"""


@contextmanager
def connect(db_path: Path | None = None):
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def has_data() -> bool:
    if not config.DB_PATH.exists():
        return False
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM measurements").fetchone()
        return row["n"] > 0


def upsert_stations(stations: list[dict]) -> None:
    with connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO stations (id, city, name, country, lat, lon) "
            "VALUES (:id, :city, :name, :country, :lat, :lon)",
            stations,
        )


def insert_measurements(rows: list[tuple]) -> None:
    """rows: (station_id, ts, pollutant, value)."""
    with connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO measurements (station_id, ts, pollutant, value) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )


def list_cities() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT city, country, COUNT(*) AS stations, AVG(lat) AS lat, AVG(lon) AS lon "
            "FROM stations GROUP BY city ORDER BY city"
        ).fetchall()
        return [dict(r) for r in rows]


def list_stations(city: str | None = None) -> list[dict]:
    with connect() as conn:
        if city:
            rows = conn.execute("SELECT * FROM stations WHERE city = ? ORDER BY name", (city,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM stations ORDER BY city, name").fetchall()
        return [dict(r) for r in rows]


def station(station_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM stations WHERE id = ?", (station_id,)).fetchone()
        return dict(row) if row else None


def latest_readings(station_id: str) -> dict:
    """Most recent value per pollutant for a station. Returns {pollutant: (value, ts)}."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT pollutant, value, ts FROM measurements m "
            "WHERE station_id = ? AND ts = ("
            "  SELECT MAX(ts) FROM measurements WHERE station_id = m.station_id AND pollutant = m.pollutant"
            ") GROUP BY pollutant",
            (station_id,),
        ).fetchall()
        return {r["pollutant"]: (r["value"], r["ts"]) for r in rows}


def series(station_id: str, pollutant: str, hours: int = 168) -> list[tuple[int, float]]:
    cutoff = int(time.time()) - hours * 3600
    with connect() as conn:
        rows = conn.execute(
            "SELECT ts, value FROM measurements WHERE station_id = ? AND pollutant = ? AND ts >= ? "
            "ORDER BY ts",
            (station_id, pollutant, cutoff),
        ).fetchall()
        return [(r["ts"], r["value"]) for r in rows]


def full_series(station_id: str, pollutant: str) -> list[tuple[int, float]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT ts, value FROM measurements WHERE station_id = ? AND pollutant = ? ORDER BY ts",
            (station_id, pollutant),
        ).fetchall()
        return [(r["ts"], r["value"]) for r in rows]
