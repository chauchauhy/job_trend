# Job Trend

Rule-based skill-trend explorer: free job APIs (JSearch / Jobicy / Remotive / RemoteOK) → skill lexicon → Streamlit chat.

## Run

```powershell
pip install -r requirements.txt
copy .env.example .env   # paste your JSearch key
streamlit run main.py
```

Key (needed only for Hong Kong):
- `JSEARCH_API_KEY` — get it at [app.openwebninja.com/api/jsearch](https://app.openwebninja.com/api/jsearch) (free tier available). HK refresh ≈ 14 requests. The key must come from the OpenWeb Ninja portal — a RapidAPI key will not work here.

USA/Global work keyless via Jobicy + Remotive + RemoteOK.

## Usage

1. Pick region (Hong Kong / USA / Global) → **Refresh jobs**.
2. Ask the chat: `top skills`, `python`, `how many jobs`, `compare hk vs usa`, `help`.
3. **Refresh jobs** always hits the APIs; badge shows 🟢 fresh / 🟠 stale. Editing `.env` or `res/config/*.json` marks caches stale automatically.

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

streamlit run app.py