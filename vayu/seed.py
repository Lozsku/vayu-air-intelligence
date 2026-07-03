"""Generate a realistic bundled air-quality dataset for APAC cities.

Produces 30 days of hourly PM2.5 / PM10 / NO2 / O3 per station with genuine
structure: diurnal traffic peaks, weekly cycles, a slow drift, sensor noise, and a
few injected pollution episodes (anomalies). Deterministic given a fixed seed so the
demo is reproducible, but anchored to "now" so the dashboard always looks live.

This guarantees the prototype works fully offline. Live OpenAQ data (ingest.py) is
merged on top when an API key + connectivity are available.
"""
from __future__ import annotations

import math
import random
import time

from . import store

# City profiles: base PM2.5 level, "peakiness", and representative stations.
# Levels are informed by typical annual conditions in each metro.
CITIES = {
    "Delhi": {
        "country": "IN", "base_pm25": 95, "amp": 0.55, "trend": 0.25,
        "stations": [
            ("delhi-anand-vihar", "Anand Vihar", 28.6469, 77.3161),
            ("delhi-rk-puram", "R.K. Puram", 28.5637, 77.1859),
        ],
        "episodes": [(6, 22, 2.1), (18, 10, 1.7)],  # (days_ago_start, duration_h, multiplier)
    },
    "Mumbai": {
        "country": "IN", "base_pm25": 52, "amp": 0.45, "trend": 0.1,
        "stations": [
            ("mumbai-bandra", "Bandra Kurla", 19.0607, 72.8687),
            ("mumbai-colaba", "Colaba", 18.9067, 72.8147),
        ],
        "episodes": [(12, 16, 1.8)],
    },
    "Bengaluru": {
        "country": "IN", "base_pm25": 41, "amp": 0.4, "trend": 0.05,
        "stations": [
            ("blr-silk-board", "Silk Board", 12.9172, 77.6228),
            ("blr-hebbal", "Hebbal", 13.0358, 77.5970),
        ],
        "episodes": [(8, 12, 1.6)],
    },
    "Jakarta": {
        "country": "ID", "base_pm25": 68, "amp": 0.5, "trend": 0.15,
        "stations": [
            ("jkt-kelapa-gading", "Kelapa Gading", -6.1588, 106.9057),
            ("jkt-kebon-jeruk", "Kebon Jeruk", -6.1935, 106.7666),
        ],
        "episodes": [(15, 20, 1.9), (4, 8, 1.5)],
    },
    "Bangkok": {
        "country": "TH", "base_pm25": 47, "amp": 0.48, "trend": 0.08,
        "stations": [
            ("bkk-chatuchak", "Chatuchak", 13.7999, 100.5540),
            ("bkk-thonburi", "Thonburi", 13.7220, 100.4870),
        ],
        "episodes": [(10, 14, 1.7)],
    },
    "Manila": {
        "country": "PH", "base_pm25": 44, "amp": 0.46, "trend": 0.06,
        "stations": [
            ("mnl-makati", "Makati", 14.5547, 121.0244),
            ("mnl-quezon", "Quezon City", 14.6760, 121.0437),
        ],
        "episodes": [(7, 10, 1.55)],
    },
}

DAYS = 30
HOURS = DAYS * 24


def _diurnal(hour: int) -> float:
    """Two traffic peaks (~8am, ~8pm), quiet pre-dawn. Returns a multiplier ~0.6-1.4."""
    morning = math.exp(-((hour - 8) ** 2) / 6.0)
    evening = math.exp(-((hour - 20) ** 2) / 8.0)
    return 0.75 + 0.55 * (morning + 0.9 * evening)


def _weekly(dow: int) -> float:
    """Weekends (5,6) somewhat cleaner."""
    return 0.85 if dow >= 5 else 1.0


def generate() -> None:
    rng = random.Random(20260704)
    store.init_db()

    now = int(time.time())
    top_of_hour = now - (now % 3600)
    start = top_of_hour - (HOURS - 1) * 3600

    stations_meta: list[dict] = []
    rows: list[tuple] = []

    for city, cfg in CITIES.items():
        for sid, sname, lat, lon in cfg["stations"]:
            stations_meta.append({
                "id": sid, "city": city, "name": sname,
                "country": cfg["country"], "lat": lat, "lon": lon,
            })
            # Small per-station offset so co-located sensors differ realistically.
            station_bias = rng.uniform(0.9, 1.12)
            for h in range(HOURS):
                ts = start + h * 3600
                lt = time.localtime(ts)
                hour, dow = lt.tm_hour, lt.tm_wday
                days_ago = (top_of_hour - ts) / 86400.0

                base = cfg["base_pm25"] * station_bias
                trend = 1.0 + cfg["trend"] * (1 - days_ago / DAYS)  # gently worsening toward now
                shape = _diurnal(hour) * _weekly(dow)
                seasonal = 1.0 + cfg["amp"] * 0.15 * math.sin(2 * math.pi * days_ago / 7)
                noise = rng.gauss(1.0, 0.12)

                pm25 = base * trend * shape * seasonal * noise

                # Injected pollution episodes (anomalies the engine should catch).
                for ep_start, ep_dur, mult in cfg["episodes"]:
                    ep_center = ep_start * 24
                    hours_from_now = days_ago * 24
                    if ep_center - ep_dur <= hours_from_now <= ep_center + ep_dur:
                        prox = 1 - abs(hours_from_now - ep_center) / ep_dur
                        pm25 *= 1 + (mult - 1) * max(0, prox)

                pm25 = max(3.0, pm25)
                # Derive correlated pollutants from PM2.5 with their own signatures.
                pm10 = pm25 * rng.uniform(1.5, 1.9)
                no2 = 18 + pm25 * 0.35 * rng.uniform(0.8, 1.2) * _diurnal(hour)
                # Ozone is anti-correlated with NO2 and peaks midday.
                o3_shape = math.exp(-((hour - 14) ** 2) / 10.0)
                o3 = 15 + 45 * o3_shape * rng.uniform(0.8, 1.15)

                rows.append((sid, ts, "pm25", round(pm25, 1)))
                rows.append((sid, ts, "pm10", round(pm10, 1)))
                rows.append((sid, ts, "no2", round(no2, 1)))
                rows.append((sid, ts, "o3", round(o3, 1)))

    store.upsert_stations(stations_meta)
    store.insert_measurements(rows)
    print(f"Seeded {len(stations_meta)} stations, {len(rows):,} measurements "
          f"({DAYS} days hourly) across {len(CITIES)} cities.")


if __name__ == "__main__":
    generate()
