# Vayu — Hackathon Prototype Submission (reference)

Everything needed for the **Hackathon Prototype Submission** form on the Hack2skill dashboard.

## Form field values

| Form field | Value |
|---|---|
| **Challenges** | AI for Better Living and Smarter Communities |
| **Working Prototype Deployed Link** | https://admit-repository-qualified-administrative.trycloudflare.com |
| **Prototype PPT/Deck (PDF)** | `Vayu_Prototype_Submission.pdf` (9 slides, 860 KB) |
| **GitHub Repository Link (Public)** | https://github.com/Lozsku/vayu-air-intelligence |
| **Demo Video Link (≤3 min)** | *(record using the script below, upload to YouTube unlisted / Drive, paste link)* |
| **Brief description of your solution** | *(see below — 995 chars, under the 1024 limit)* |

## Brief description (paste into the form)

> Vayu (वायु) is an AI Decision Intelligence platform for community air quality and health. Instead of just showing AQI numbers, it answers plain-language questions like "Is it safe for my kid to play outside in Delhi this evening?" with a fast, forecast-backed, population-aware recommendation. An explainable engine computes US-EPA AQI, a 24-hour forecast with a confidence band, and detects pollution episodes; a Gemini-powered assistant then narrates only those verified facts — so it never invents numbers — and falls back to a local model when no cloud key is present, so it never goes dark. Every answer ships with a "Why this answer?" panel for full transparency. It covers 6 APAC cities across 12 stations, exposes a REST API and a live dashboard, containerizes for Cloud Run or any VM, and is deployed live over HTTPS today. Vayu turns open city data into faster, better health decisions for citizens, schools, and city stakeholders.

## 3-minute demo video script (screen-record the live app)

**Open the live app full-screen:** https://admit-repository-qualified-administrative.trycloudflare.com

**[0:00–0:25] Hook + problem**
> "Every city publishes air-quality data — but a parent still can't get a straight answer to the one question that matters: given the air right now and where it's heading, what should I *do*? Meet Vayu — AI decision intelligence for community air and health."
Show the dashboard loading, cities ranked worst-air-first.

**[0:25–1:05] Ask Vayu (the core)**
Click the chip **"Is it safe for my kid to play outside in Delhi this evening?"**
> "I ask in plain English. Vayu doesn't just show a number — it gives a verdict: *take care*. It says Delhi is 158, Unhealthy, driven by PM2.5, and — crucially — forecasts a peak of 218 tonight. For a child, not advisable."
Expand **"Why this answer?"**.
> "And it's grounded — the AI only narrates facts the engine computed. No hallucinated numbers. That's responsible AI."

**[1:05–1:45] The intelligence**
Point to the gauge, pollutant cards, and the chart.
> "Under the hood: standard US-EPA AQI, a 24-hour forecast with a confidence band, and automatic pollution-episode detection — here it caught a PM2.5 spike of 207 against a 113 baseline."
Change the **profile** dropdown to *asthma* → decision updates.
> "Recommendations adapt to who you are — children, elderly, asthma, or someone planning a run."

**[1:45–2:20] Breadth + alerts**
Click **Jakarta**, then type **"Should I go for a run in Bangkok tomorrow morning?"**
> "Six APAC cities, and a live cross-city alert feed — the push layer for schools and city stakeholders to act faster."

**[2:20–3:00] Tech + close**
> "Vayu is built Google-Cloud-first: a Gemini assistant, a BigQuery-ready time-series lake, and one-command Cloud Run deploy — it's live over HTTPS right now. It turns open data into faster, better decisions for everyone. Vayu — build in APAC, build for the world."
Show the GitHub badge / repo.

**Tips:** keep it under 3:00, 1080p, no dead air. Try the shareable deep link
`/?ask=Should%20I%20go%20for%20a%20run%20in%20Bangkok%20tomorrow%20morning%3F` to pre-load a question on camera.
