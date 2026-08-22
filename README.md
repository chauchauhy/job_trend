# Job Trend

Rule-based skill-trend explorer: free job APIs (JSearch / Jooble / Jobicy / Remotive / RemoteOK) → skill lexicon → Streamlit chat.

## Run

```powershell
pip install -r requirements.txt
copy .env.example .env   # paste your keys
streamlit run main.py
```

Keys (both optional, at least one needed for Hong Kong):
- `JSEARCH_API_KEY` — RapidAPI [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) BASIC plan (free 200 req/month, no card). HK refresh ≈ 14 requests.
- `JOOBLE_API_KEY` — jooble.org fallback for HK.

USA/Global work keyless via Jobicy + Remotive + RemoteOK.

## Usage

1. Pick region (Hong Kong / USA / Global) → **Refresh jobs**.
2. Ask the chat: `top skills`, `python`, `how many jobs`, `compare hk vs usa`, `help`.
3. Results cached 6h in memory + `res/data/*.json`; **Force refresh** bypasses TTL.

## Layout

```
config.py            settings (dataclasses, reads .env)
main.py              entry point
res/config/          keywords.json (search terms), skills.json (editable skill lexicon)
res/data/            per-region disk cache
src/app.py           Streamlit UI (sidebar, dashboard, chat)
src/fetch.py         orchestration: fetch, dedupe, region filter, relevance, cache
src/sources/         one adapter per API
src/analysis/skills.py   frequency engine
src/chat/handler.py  intent routing for the chat
tests/               pytest, no live APIs
```

Tuning: edit `res/config/skills.json` (skills/aliases) or `res/config/keywords.json` (search queries, relevance terms) and hit Force refresh.
