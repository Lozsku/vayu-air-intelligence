"""US EPA Air Quality Index computation and health guidance.

Real domain logic: converts raw pollutant concentrations (ug/m3, or ppb for gases)
into the standard 0-500 AQI scale using EPA breakpoints, then maps to categories and
population-specific health advice. This is the deterministic backbone the AI assistant
reasons over — so recommendations are grounded, explainable, and reproducible.
"""
from __future__ import annotations

# Concentration truncation precision per EPA before AQI lookup (decimals).
# This is required: EPA breakpoints are contiguous only once the concentration is
# truncated (e.g. PM10 54.4 -> 54), otherwise values fall in the integer "gaps".
_PRECISION = {"pm25": 1, "pm10": 0, "o3": 0, "no2": 0}

# EPA breakpoints: (C_low, C_high, I_low, I_high) per pollutant.
# PM2.5 / PM10 in ug/m3 (24h), O3 / NO2 in ppb. Values are the standard EPA tables.
_BREAKPOINTS = {
    "pm25": [
        (0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 500.4, 301, 500),
    ],
    "pm10": [
        (0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150),
        (255, 354, 151, 200), (355, 424, 201, 300), (425, 604, 301, 500),
    ],
    "o3": [  # 8-hour ppb
        (0, 54, 0, 50), (55, 70, 51, 100), (71, 85, 101, 150),
        (86, 105, 151, 200), (106, 200, 201, 300),
    ],
    "no2": [  # 1-hour ppb
        (0, 53, 0, 50), (54, 100, 51, 100), (101, 360, 101, 150),
        (361, 649, 151, 200), (650, 1249, 201, 300), (1250, 2049, 301, 500),
    ],
}

CATEGORIES = [
    (0, 50, "Good", "#2ecc71"),
    (51, 100, "Moderate", "#f1c40f"),
    (101, 150, "Unhealthy for Sensitive Groups", "#e67e22"),
    (151, 200, "Unhealthy", "#e74c3c"),
    (201, 300, "Very Unhealthy", "#8e44ad"),
    (301, 500, "Hazardous", "#7e0023"),
]

POLLUTANT_LABELS = {
    "pm25": "PM2.5", "pm10": "PM10", "o3": "Ozone", "no2": "NO₂",
}


def sub_index(pollutant: str, concentration: float) -> float | None:
    """AQI sub-index for one pollutant concentration via linear interpolation."""
    table = _BREAKPOINTS.get(pollutant)
    if table is None or concentration is None:
        return None
    # Truncate to EPA precision so the value lands cleanly inside a breakpoint band.
    c = round(max(0.0, float(concentration)), _PRECISION.get(pollutant, 0))
    for c_lo, c_hi, i_lo, i_hi in table:
        if c_lo <= c <= c_hi:
            return round((i_hi - i_lo) / (c_hi - c_lo) * (c - c_lo) + i_lo)
    # Above the top breakpoint — clamp to the max index.
    return table[-1][3]


def aqi_from_pollutants(readings: dict[str, float]) -> dict:
    """Overall AQI = max of sub-indices. Returns AQI, dominant pollutant, category."""
    subs = {}
    for pol, val in readings.items():
        si = sub_index(pol, val)
        if si is not None:
            subs[pol] = si
    if not subs:
        return {"aqi": None, "dominant": None, "category": None, "color": None, "subindices": {}}
    dominant = max(subs, key=subs.get)
    aqi = subs[dominant]
    cat, color = category_for(aqi)
    return {
        "aqi": aqi,
        "dominant": dominant,
        "dominant_label": POLLUTANT_LABELS.get(dominant, dominant),
        "category": cat,
        "color": color,
        "subindices": subs,
    }


def category_for(aqi: float) -> tuple[str, str]:
    for lo, hi, name, color in CATEGORIES:
        if lo <= aqi <= hi:
            return name, color
    return ("Hazardous", "#7e0023")


# Population-specific health guidance keyed by category index.
_ADVICE = {
    "Good": {
        "general": "Air quality is healthy. A great day to be outdoors.",
        "sensitive": "No precautions needed.",
        "outdoor_ok": True,
    },
    "Moderate": {
        "general": "Air quality is acceptable for most people.",
        "sensitive": "Unusually sensitive individuals should consider limiting prolonged outdoor exertion.",
        "outdoor_ok": True,
    },
    "Unhealthy for Sensitive Groups": {
        "general": "Most people are unaffected, but sensitive groups should take care.",
        "sensitive": "Children, elderly, and people with asthma/heart conditions should reduce prolonged or heavy outdoor exertion.",
        "outdoor_ok": False,
    },
    "Unhealthy": {
        "general": "Everyone may begin to experience health effects; limit prolonged outdoor exertion.",
        "sensitive": "Sensitive groups should avoid outdoor activity and keep reliever medication handy.",
        "outdoor_ok": False,
    },
    "Very Unhealthy": {
        "general": "Health alert: everyone should avoid outdoor exertion and keep windows closed.",
        "sensitive": "Sensitive groups should remain indoors with air purification if available.",
        "outdoor_ok": False,
    },
    "Hazardous": {
        "general": "Emergency conditions: everyone should stay indoors and use N95 masks if going out is unavoidable.",
        "sensitive": "Sensitive groups are at serious risk — stay indoors with purified air.",
        "outdoor_ok": False,
    },
}


def advice_for(category: str) -> dict:
    return _ADVICE.get(category, _ADVICE["Hazardous"])
