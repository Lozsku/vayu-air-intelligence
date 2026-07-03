"""Analytics engine: forecasting, anomaly detection, and AQI roll-ups.

Lightweight and explainable by design (no black-box model): a 24-hour forecast is a
seasonal (hour-of-day) profile scaled by a recent linear trend, with a residual-based
confidence band. Anomalies use a robust rolling median + MAD z-score. Every number the
AI assistant cites traces back to one of these transparent computations.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import numpy as np

from . import aqi, store

FORECAST_HORIZON = 24  # hours
ANOMALY_Z = 3.5        # MAD z-score threshold for a flagged episode


# ----------------------------- forecasting ---------------------------------- #
def forecast(station_id: str, pollutant: str, horizon: int = FORECAST_HORIZON) -> dict:
    hist = store.full_series(station_id, pollutant)
    if len(hist) < 48:
        return {"points": [], "method": "insufficient-data"}

    ts = np.array([t for t, _ in hist], dtype=np.int64)
    vals = np.array([v for _, v in hist], dtype=float)

    hours = np.array([datetime.fromtimestamp(t).hour for t in ts])
    # Hour-of-day seasonal profile from the most recent 14 days.
    recent_mask = ts >= (ts[-1] - 14 * 86400)
    profile = np.array([
        vals[recent_mask & (hours == h)].mean() if np.any(recent_mask & (hours == h))
        else vals.mean()
        for h in range(24)
    ])

    # Recent linear trend on the last 7 days of daily means.
    day_idx = (ts - ts[0]) // 86400
    last_days = np.unique(day_idx)[-7:]
    daily_means = np.array([vals[day_idx == d].mean() for d in last_days])
    if len(daily_means) >= 2:
        x = np.arange(len(daily_means))
        slope = np.polyfit(x, daily_means, 1)[0]
    else:
        slope = 0.0

    # Residuals of history vs its own seasonal profile → confidence band.
    fitted = profile[hours]
    resid_std = float(np.std(vals - fitted))

    last_ts = int(ts[-1])
    base_level = float(daily_means[-1]) if len(daily_means) else float(vals[-1])
    profile_mean = float(profile.mean()) or 1.0

    points = []
    for h in range(1, horizon + 1):
        ft = last_ts + h * 3600
        hod = datetime.fromtimestamp(ft).hour
        # Seasonal shape scaled to the trending base level, nudged by slope.
        seasonal = profile[hod] / profile_mean
        level = base_level + slope * (h / 24.0)
        yhat = max(1.0, seasonal * level)
        band = 1.96 * resid_std * (1 + h / horizon)  # widens with horizon
        points.append({
            "ts": ft,
            "yhat": round(yhat, 1),
            "low": round(max(0.0, yhat - band), 1),
            "high": round(yhat + band, 1),
        })

    trend_word = "worsening" if slope > 0.5 else "improving" if slope < -0.5 else "stable"
    return {
        "points": points,
        "method": "seasonal-profile + linear-trend",
        "trend": trend_word,
        "slope_per_day": round(float(slope), 2),
        "resid_std": round(resid_std, 1),
    }


# ---------------------------- anomaly detection ----------------------------- #
def anomalies(station_id: str, pollutant: str, window: int = 24, lookback_h: int = 168) -> list[dict]:
    ser = store.series(station_id, pollutant, hours=lookback_h)
    if len(ser) < window + 2:
        return []
    ts = np.array([t for t, _ in ser])
    vals = np.array([v for _, v in ser], dtype=float)

    out = []
    for i in range(window, len(vals)):
        ref = vals[i - window:i]
        med = np.median(ref)
        mad = np.median(np.abs(ref - med)) or 1e-6
        z = 0.6745 * (vals[i] - med) / mad  # robust modified z-score
        if z >= ANOMALY_Z:
            out.append({
                "ts": int(ts[i]),
                "value": round(float(vals[i]), 1),
                "baseline": round(float(med), 1),
                "z": round(float(z), 1),
                "pollutant": pollutant,
                "label": aqi.POLLUTANT_LABELS.get(pollutant, pollutant),
            })
    return out


# ------------------------------ AQI roll-ups -------------------------------- #
def station_snapshot(station_id: str) -> dict:
    st = store.station(station_id)
    if not st:
        return {}
    latest = store.latest_readings(station_id)
    readings = {pol: val for pol, (val, _ts) in latest.items()}
    idx = aqi.aqi_from_pollutants(readings)
    ts = max((t for _v, t in latest.values()), default=None)
    return {
        "station": st,
        "readings": {pol: {"value": round(val, 1), "label": aqi.POLLUTANT_LABELS.get(pol, pol)}
                     for pol, val in readings.items()},
        "aqi": idx,
        "ts": ts,
        "updated": _iso(ts) if ts else None,
    }


def city_snapshot(city: str) -> dict:
    stations = store.list_stations(city)
    snaps = [station_snapshot(s["id"]) for s in stations]
    snaps = [s for s in snaps if s.get("aqi", {}).get("aqi") is not None]
    if not snaps:
        return {"city": city, "aqi": None, "stations": []}
    worst = max(snaps, key=lambda s: s["aqi"]["aqi"])
    avg = round(sum(s["aqi"]["aqi"] for s in snaps) / len(snaps))
    cat, color = aqi.category_for(avg)
    return {
        "city": city,
        "aqi": avg,
        "category": cat,
        "color": color,
        "worst_station": worst["station"]["name"],
        "worst_aqi": worst["aqi"]["aqi"],
        "stations": snaps,
    }


def decision(station_id: str, profile: str = "general", activity: str | None = None) -> dict:
    """The core 'decision intelligence' output: current + forecast AQI → a concrete
    recommendation for a given population profile and planned activity."""
    snap = station_snapshot(station_id)
    if not snap:
        return {}
    dominant = snap["aqi"]["dominant"] or "pm25"
    fc = forecast(station_id, dominant)

    # Peak forecast AQI over the next horizon.
    peak_aqi, peak_ts = snap["aqi"]["aqi"], snap["ts"]
    for p in fc.get("points", []):
        a = aqi.sub_index(dominant, p["yhat"])
        if a is not None and a > peak_aqi:
            peak_aqi, peak_ts = a, p["ts"]
    peak_cat, _ = aqi.category_for(peak_aqi)
    adv = aqi.advice_for(peak_cat)

    sensitive = profile in ("child", "elderly", "asthma", "sensitive", "pregnant")
    guidance = adv["sensitive"] if sensitive else adv["general"]
    safe = adv["outdoor_ok"] and not (sensitive and peak_aqi > 100)

    return {
        "station": snap["station"],
        "now": {"aqi": snap["aqi"]["aqi"], "category": snap["aqi"]["category"]},
        "forecast_peak": {"aqi": peak_aqi, "category": peak_cat, "at": _iso(peak_ts)},
        "trend": fc.get("trend", "stable"),
        "dominant": aqi.POLLUTANT_LABELS.get(dominant, dominant),
        "profile": profile,
        "activity": activity,
        "safe_outdoors": safe,
        "guidance": guidance,
    }


def _iso(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat()
