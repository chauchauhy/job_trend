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

1. Pick region (Hong Kong / USA / Global). First visit auto-pulls; **⟳ Refresh** stays disabled until the current pull is older than `refresh_unlock_days` (7, see `config.py`).
2. Sidebar **My stack**: tick the skills you know — the Skill demand bars mark them with ✓ and a line lists the top-demand skills missing from your stack.
3. **Skill trends** records one snapshot per successful pull (`res/data/history_<region>.json`, tracked in git) so lines build up across pulls.
4. Headless collection without opening the UI:

   ```powershell
   .venv\Scripts\python.exe scripts\update_history.py               # all regions
   .venv\Scripts\python.exe scripts\update_history.py --regions hk  # subset (aliases: hk, usa, global)
   ```

5. Ask the chat: `top skills`, `python`, `how many jobs`, `compare hk vs usa`, `help`. Editing `.env` or `res/config/*.json` marks caches stale automatically.

## Layout

```
config.py            settings (dataclasses, reads .env)
main.py              entry point
scripts/             update_history.py headless collector
res/config/          keywords.json (search terms), skills.json (editable skill lexicon)
res/data/            per-region disk cache + history snapshots + my_skills.json
src/app.py           Streamlit UI (topbar, sidebar, dashboard, trends, chat)
src/fetch.py         orchestration: fetch, dedupe, region filter, relevance, cache, pull_and_record
src/sources/         one adapter per API
src/analysis/        skills.py frequency engine · history.py snapshots · gap.py my-stack matching
src/chat/handler.py  intent routing for the chat
tests/               pytest, no live APIs
```

Tuning: edit `res/config/skills.json` (skills/aliases) or `res/config/keywords.json` (search queries, relevance terms); the next pull picks changes up and the FRESH/STALE chip reflects them.