"""Ask Vayu — natural-language decision assistant.

Turns a plain-English question ("Is it safe for my kid to play outside in Delhi this
evening?") into a grounded, explainable answer. The engine computes the facts
(current AQI, 24h forecast, anomalies, a recommendation); the LLM only *narrates* those
facts — so answers are trustworthy and never hallucinate numbers. If no cloud LLM is
configured, a deterministic composer produces the same answer locally.
"""
from __future__ import annotations

from . import engine, llm, store

_PROFILE_KEYWORDS = {
    "child": ["kid", "child", "children", "toddler", "baby", "school", "son", "daughter"],
    "elderly": ["elderly", "grandmother", "grandfather", "grandparent", "senior", "old"],
    "asthma": ["asthma", "asthmatic", "copd", "respiratory", "lungs", "wheez"],
    "pregnant": ["pregnant", "pregnancy", "expecting"],
    "athlete": ["run", "running", "jog", "cycle", "cycling", "workout", "exercise", "marathon", "practice", "training"],
}

_ACTIVITY_KEYWORDS = ["run", "jog", "cycle", "walk", "play", "practice", "exercise",
                      "school", "commute", "outdoor", "picnic", "match", "game"]

SYSTEM = (
    "You are Vayu, an air-quality decision assistant for communities in the Asia-Pacific. "
    "You are given verified facts computed by an analytics engine (current AQI, a 24-hour "
    "forecast, detected pollution episodes, and a recommendation). Answer the user's "
    "question in 3-5 sentences, plain and warm, for a non-expert. Use ONLY the numbers in "
    "the facts — never invent values. Give one clear, actionable recommendation, mention the "
    "best time window if relevant, and note the dominant pollutant. Do not add disclaimers."
)


def resolve_city(question: str) -> str | None:
    q = question.lower()
    for c in store.list_cities():
        if c["city"].lower() in q:
            return c["city"]
    return None


def resolve_profile(question: str) -> str:
    q = question.lower()
    for profile, kws in _PROFILE_KEYWORDS.items():
        if any(k in q for k in kws):
            return "child" if profile == "child" else profile
    return "general"


def resolve_activity(question: str) -> str | None:
    q = question.lower()
    for a in _ACTIVITY_KEYWORDS:
        if a in q:
            return a
    return None


def _facts(city: str, profile: str, activity: str | None) -> dict:
    snap = engine.city_snapshot(city)
    if not snap.get("stations"):
        return {}
    worst = max(snap["stations"], key=lambda s: s["aqi"]["aqi"])
    sid = worst["station"]["id"]
    dec = engine.decision(sid, profile=profile, activity=activity)
    dominant = worst["aqi"]["dominant"] or "pm25"
    fc = engine.forecast(sid, dominant)
    anos = engine.anomalies(sid, dominant)
    return {"city": city, "snapshot": snap, "decision": dec, "forecast": fc,
            "anomalies": anos, "station": worst["station"]["name"]}


def _local_answer(f: dict, profile: str) -> str:
    dec = f["decision"]
    city = f["city"]
    now = dec["now"]
    peak = dec["forecast_peak"]
    verb = "safe" if dec["safe_outdoors"] else "not advisable"
    who = {"child": "children", "elderly": "elderly people", "asthma": "people with asthma",
           "pregnant": "expecting mothers", "athlete": "people exercising"}.get(profile, "most people")
    parts = [
        f"In {city}, the air right now is {now['aqi']} AQI ({now['category']}), driven by "
        f"{dec['dominant']}, and the 24-hour trend is {dec['trend']}.",
        f"It is expected to peak around {peak['aqi']} AQI ({peak['category']}) near "
        f"{peak['at'][11:16] if peak.get('at') else 'later today'}.",
        f"For {who}, outdoor activity is currently {verb}. {dec['guidance']}",
    ]
    if f.get("anomalies"):
        a = f["anomalies"][-1]
        parts.append(f"Note: a pollution spike was detected recently ({a['label']} hit "
                     f"{a['value']} vs a {a['baseline']} baseline).")
    return " ".join(parts)


_SUPERLATIVE_KW = ["which city", "worst air", "most polluted", "cleanest", "best air",
                   "safest city", "worst city", "rank the cit", "compare cit"]


def _compare_cities(question: str) -> dict:
    """Answer cross-city superlative questions ('which city has the worst air?')."""
    ranked = []
    for c in store.list_cities():
        snap = engine.city_snapshot(c["city"])
        if snap.get("aqi") is not None:
            ranked.append((c["city"], snap["aqi"], snap["category"]))
    if not ranked:
        return {"answer": "I don't have data loaded yet.", "backend": "local"}
    ranked.sort(key=lambda x: x[1], reverse=True)  # worst first
    want_best = any(k in question for k in ["cleanest", "best air", "safest"])
    pick = ranked[-1] if want_best else ranked[0]
    board = "; ".join(f"{n} {a} ({cat})" for n, a, cat in ranked)
    which = "cleanest" if want_best else "most polluted"
    text = (f"Right now {pick[0]} has the {which} air at {pick[1]} AQI ({pick[2]}). "
            f"Across the cities I track (worst to best): {board}.")
    return {"answer": text, "backend": "local", "city": pick[0],
            "ranking": [{"city": n, "aqi": a, "category": cat} for n, a, cat in ranked]}


def answer(question: str, city: str | None = None) -> dict:
    # Cross-city superlative questions don't depend on a single selected city.
    mentioned = resolve_city(question)
    if not mentioned and any(k in question.lower() for k in _SUPERLATIVE_KW):
        return _compare_cities(question.lower())
    # A city named in the question always wins over the UI's current selection.
    city = mentioned or city
    if not city:
        cities = ", ".join(c["city"] for c in store.list_cities())
        return {"answer": f"Which city would you like to check? I currently track: {cities}.",
                "backend": "local", "needs_city": True}

    profile = resolve_profile(question)
    activity = resolve_activity(question)
    f = _facts(city, profile, activity)
    if not f:
        return {"answer": f"I don't have live data for {city} yet.", "backend": "local"}

    local = _local_answer(f, profile)

    backend = llm.available()
    if backend == "local":
        text = local
    else:
        dec, fc = f["decision"], f["forecast"]
        prompt = (
            f"Question: {question}\n\nVerified facts:\n"
            f"- City: {city} (worst station: {f['station']})\n"
            f"- Current AQI: {dec['now']['aqi']} ({dec['now']['category']}), dominant pollutant {dec['dominant']}\n"
            f"- 24h trend: {dec['trend']} (slope {fc.get('slope_per_day')}/day)\n"
            f"- Forecast peak: {dec['forecast_peak']['aqi']} AQI ({dec['forecast_peak']['category']}) "
            f"around {dec['forecast_peak'].get('at')}\n"
            f"- Population profile: {profile}; planned activity: {activity or 'unspecified'}\n"
            f"- Engine recommendation: outdoor activity {'SAFE' if dec['safe_outdoors'] else 'NOT advised'}; "
            f"{dec['guidance']}\n"
            f"- Recent pollution episodes: {len(f['anomalies'])} detected\n"
        )
        text, backend = llm.complete(prompt, system=SYSTEM)
        if not text or len(text) < 20:
            text, backend = local, "local"

    return {
        "answer": text,
        "backend": backend,
        "city": city,
        "profile": profile,
        "activity": activity,
        "decision": f["decision"],
        "forecast": f["forecast"],
        "anomalies": f["anomalies"][-5:],
        "grounded_on": local,  # transparency: the deterministic facts behind the narration
    }
