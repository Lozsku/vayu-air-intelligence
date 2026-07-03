<div align="center">

# वायु · Vayu

### AI Decision Intelligence for Community Air Quality & Health

**Ask a question in plain language. Get a fast, forecast-backed, explainable decision.**

*Built for the Gen AI Academy APAC Edition Hackathon — "AI for Better Living and Smarter Communities."*

[Live demo](https://admit-repository-qualified-administrative.trycloudflare.com) · Provider-agnostic AI (Gemini / OpenAI / local)

</div>

---

## The problem

Every APAC megacity now publishes air-quality data — but a parent, a runner, a school
administrator, or a city official still can't get a straight answer to the only question
that matters: **"Given the air right now and where it's heading, what should I *do*?"**

Dashboards show numbers. People need **decisions**. And they need them in seconds, not
after an analyst digs through charts.

## What Vayu does

Vayu is a **Decision Intelligence Platform** for air quality. It ingests community
sensor data, computes the standard AQI, **forecasts the next 24 hours**, **detects
pollution episodes**, and turns all of it into a **specific, population-aware
recommendation** — narrated by an LLM but *grounded* on transparent computations so it
never invents numbers.

> **"Is it safe for my kid to play outside in Delhi this evening?"**
> → *"Air in Delhi is 158 AQI (Unhealthy), driven by PM2.5, and expected to peak at 218
> (Very Unhealthy) around 8:30. For children, outdoor play is not advisable right now —
> better after tomorrow noon. A pollution spike was detected last night (PM2.5 207 vs a
> 113 baseline)."*

### The "acceleration" story
What a citizen would otherwise do — open a portal, find the nearest station, read four
pollutant numbers, guess the trend, translate it to a health decision — Vayu collapses
into **one sentence, in under a second.** Faster and better decisions, for everyone.

## Features

| Capability | How it works |
|---|---|
| 🗣️ **Ask Vayu** (NL assistant) | Plain-English question → grounded, explainable answer + recommendation |
| 📊 **Standard AQI** | US EPA breakpoints for PM2.5, PM10, NO₂, O₃ with dominant-pollutant attribution |
| 🔮 **24-hour forecast** | Seasonal hour-of-day profile × recent trend, with a confidence band |
| 🚨 **Anomaly detection** | Robust rolling median + MAD z-score flags real pollution episodes |
| 🧑‍⚕️ **Population-aware decisions** | Tailored guidance for children, elderly, asthma, pregnancy, outdoor exercise |
| 📡 **Live alerts feed** | Cross-city unhealthy-air + episode alerts — the push layer for city stakeholders |
| 🌏 **6 APAC cities** | Delhi, Mumbai, Bengaluru, Jakarta, Bangkok, Manila (12 stations) |

## Why it's trustworthy (Responsible AI)

The LLM **only narrates facts the engine computed** — current AQI, forecast, anomalies,
and a rule-based recommendation. Every answer ships with a **"Why this answer?"** panel
exposing the exact numbers behind it. No hallucinated readings, ever. And the assistant
works **fully offline**: with no cloud key it falls back to a deterministic composer, so
the tool never goes dark.

## Architecture

```
Community sensors / OpenAQ ─▶ SQLite time-series store
                                     │
             ┌───────────────────────┼───────────────────────┐
             ▼                       ▼                        ▼
     AQI engine (EPA)        Forecast (seasonal+trend)   Anomaly (MAD z-score)
             └───────────────────────┼───────────────────────┘
                                     ▼
                        Decision engine (population-aware)
                                     ▼
                 Ask Vayu  ◀── provider-agnostic LLM (Gemini│OpenAI│local)
                                     ▼
                     Flask API  +  live dashboard (Chart.js)
```

The time-series engine is a civic re-point of a production real-time analytics platform
we built for financial markets — the station × metric × time shape is identical, which
is exactly why forecasting and anomaly detection transferred directly.

## Tech

Python · Flask · NumPy · SQLite · Chart.js · Google Gemini (`google-genai`, optional) ·
OpenAQ (optional live data) · deployable on Cloud Run or any VM. Zero external runtime
JS dependencies (Chart.js vendored).

## Run locally

```bash
cd vayu
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional — add GEMINI_API_KEY for cloud AI
python app.py               # http://localhost:8095
```

First boot auto-seeds a realistic 30-day hourly dataset for all six cities (and enriches
it with live OpenAQ data if `OPENAQ_API_KEY` is set).

### Enable Gemini
Set `GEMINI_API_KEY` in `.env`. The badge in the header flips from `AI: local` to
`AI: gemini` and answers are narrated by Gemini — grounded on the same engine facts.

## API

| Endpoint | Returns |
|---|---|
| `GET /api/cities` | All cities with current AQI, worst-air-first |
| `GET /api/city/<city>` | Per-station snapshot for a city |
| `GET /api/station/<id>/forecast?pollutant=pm25` | 24h forecast + confidence band |
| `GET /api/station/<id>/anomalies?pollutant=pm25` | Detected pollution episodes |
| `GET /api/station/<id>/decision?profile=child` | Population-aware recommendation |
| `POST /api/ask` `{question, city?}` | Natural-language answer |
| `GET /api/alerts` | Cross-city alert feed |

## Project layout

```
vayu/
├── app.py               # Flask entry (serves dashboard + API)
├── vayu/
│   ├── aqi.py           # EPA AQI + health guidance
│   ├── engine.py        # forecast, anomaly detection, decisions
│   ├── assistant.py     # NL question → grounded answer
│   ├── llm.py           # provider-agnostic LLM (Gemini/OpenAI/local)
│   ├── ingest.py        # optional live OpenAQ enrichment
│   ├── seed.py          # realistic bundled dataset generator
│   ├── store.py         # SQLite time-series store
│   └── api.py           # Flask blueprint
└── static/              # dashboard (HTML/CSS/JS, Chart.js vendored)
```

## License

MIT — see [LICENSE](LICENSE).
