"""Flask API blueprint for Vayu."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from . import __version__, aqi, assistant, config, engine, llm, store

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/health")
def health():
    return jsonify({"status": "ok", "version": __version__})


@api.get("/meta")
def meta():
    return jsonify({
        "version": __version__,
        "ai_backend": llm.available(),
        "cities": [c["city"] for c in store.list_cities()],
        "live_data": bool(config.OPENAQ_API_KEY),
    })


@api.get("/cities")
def cities():
    out = []
    for c in store.list_cities():
        snap = engine.city_snapshot(c["city"])
        out.append({
            "city": c["city"], "country": c.get("country"),
            "lat": c["lat"], "lon": c["lon"],
            "aqi": snap.get("aqi"), "category": snap.get("category"),
            "color": snap.get("color"),
            "worst_station": snap.get("worst_station"),
            "stations": len(snap.get("stations", [])),
        })
    out.sort(key=lambda x: (x["aqi"] is None, -(x["aqi"] or 0)))
    return jsonify(out)


@api.get("/city/<city>")
def city(city: str):
    return jsonify(engine.city_snapshot(city))


@api.get("/station/<station_id>")
def station(station_id: str):
    return jsonify(engine.station_snapshot(station_id))


@api.get("/station/<station_id>/series")
def station_series(station_id: str):
    pollutant = request.args.get("pollutant", "pm25")
    hours = int(request.args.get("hours", 168))
    ser = store.series(station_id, pollutant, hours=hours)
    return jsonify({
        "pollutant": pollutant,
        "label": aqi.POLLUTANT_LABELS.get(pollutant, pollutant),
        "points": [{"ts": t, "value": v} for t, v in ser],
    })


@api.get("/station/<station_id>/forecast")
def station_forecast(station_id: str):
    pollutant = request.args.get("pollutant", "pm25")
    return jsonify(engine.forecast(station_id, pollutant))


@api.get("/station/<station_id>/anomalies")
def station_anomalies(station_id: str):
    pollutant = request.args.get("pollutant", "pm25")
    return jsonify(engine.anomalies(station_id, pollutant))


@api.get("/station/<station_id>/decision")
def station_decision(station_id: str):
    profile = request.args.get("profile", "general")
    activity = request.args.get("activity")
    return jsonify(engine.decision(station_id, profile=profile, activity=activity))


@api.post("/ask")
def ask():
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    city = body.get("city")
    if not question:
        return jsonify({"error": "question is required"}), 400
    return jsonify(assistant.answer(question, city=city))


@api.get("/alerts")
def alerts():
    """Cross-city anomaly + unhealthy-air feed — the 'push' layer for city stakeholders."""
    feed = []
    for c in store.list_cities():
        snap = engine.city_snapshot(c["city"])
        if snap.get("aqi") and snap["aqi"] > 150:
            feed.append({
                "type": "unhealthy", "city": c["city"], "aqi": snap["aqi"],
                "category": snap["category"], "station": snap.get("worst_station"),
            })
        for s in snap.get("stations", []):
            dom = s["aqi"].get("dominant") or "pm25"
            for a in engine.anomalies(s["station"]["id"], dom, lookback_h=48):
                feed.append({
                    "type": "episode", "city": c["city"],
                    "station": s["station"]["name"], "pollutant": a["label"],
                    "value": a["value"], "baseline": a["baseline"], "ts": a["ts"],
                })
    feed.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return jsonify(feed[:20])
