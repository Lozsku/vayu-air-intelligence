"""Optional live enrichment from OpenAQ v3.

Best-effort: if OPENAQ_API_KEY is set and the network is reachable, pull the latest
real measurements for our tracked stations' cities and merge them into the store so the
dashboard reflects genuine current conditions. On any failure it silently no-ops — the
bundled dataset keeps the demo fully functional.
"""
from __future__ import annotations

import time

import requests

from . import config, store

OPENAQ_BASE = "https://api.openaq.org/v3"
_PARAM_MAP = {"pm25": "pm25", "pm10": "pm10", "no2": "no2", "o3": "o3"}


def enrich_live(max_cities: int = 6) -> dict:
    if not config.OPENAQ_API_KEY:
        return {"ok": False, "reason": "no OPENAQ_API_KEY; using bundled data"}
    headers = {"X-API-Key": config.OPENAQ_API_KEY}
    inserted = 0
    try:
        cities = store.list_cities()[:max_cities]
        for c in cities:
            # Find nearby OpenAQ locations by coordinate, pull latest measurements.
            r = requests.get(
                f"{OPENAQ_BASE}/locations",
                params={"coordinates": f"{c['lat']},{c['lon']}", "radius": 25000, "limit": 5},
                headers=headers, timeout=8,
            )
            if r.status_code != 200:
                continue
            for loc in r.json().get("results", []):
                lr = requests.get(
                    f"{OPENAQ_BASE}/locations/{loc['id']}/latest",
                    headers=headers, timeout=8,
                )
                if lr.status_code != 200:
                    continue
                sid = f"live-{loc['id']}"
                store.upsert_stations([{
                    "id": sid, "city": c["city"], "name": loc.get("name", "OpenAQ")[:60],
                    "country": c.get("country"), "lat": loc.get("coordinates", {}).get("latitude"),
                    "lon": loc.get("coordinates", {}).get("longitude"),
                }])
                rows = []
                now = int(time.time())
                ts = now - (now % 3600)
                for m in lr.json().get("results", []):
                    pol = _PARAM_MAP.get((m.get("parameter") or {}).get("name"))
                    val = m.get("value")
                    if pol and val is not None:
                        rows.append((sid, ts, pol, float(val)))
                if rows:
                    store.insert_measurements(rows)
                    inserted += len(rows)
        return {"ok": True, "inserted": inserted}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": str(exc)}
