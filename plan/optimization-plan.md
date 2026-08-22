# Job Trend — Code Review & Optimization Plan

Rule-based Streamlit explorer: Jooble + Jobicy + Remotive → skill lexicon → chat.

The pipeline is small and readable. Biggest issues are **wrong region data**, **noisy skill matching**, **unused cache/TTL**, and **missing project hygiene**.

---

## Current architecture

```
streamlit run main.py
        └── src.app.run()
                │
                ├── sidebar: region + Refresh
                │         └── src.fetch.refresh_region(region)
                │                   ├── jooble.fetch()              always (if API key)
                │                   ├── jobicy + remotive           USA / Global only
                │                   ├── dedupe by URL or title|company
                │                   ├── relevance filter (title + tags)
                │                   └── cap at max_jobs_per_region (150)
                │
                ├── src.analysis.skills.compute_stats(jobs)
                │         └── SkillMatcher vs res/config/skills.json
                │
                └── chat → src.chat.handler.respond()
                          intents: help | compare | job count | top skills | skill name
```

| Layer | Module | Role |
|---|---|---|
| UI | `src/app.py` | Page config, sidebar, chat history, refresh trigger |
| Orchestration | `src/fetch.py` | Multi-source fetch, merge/dedupe, relevance, warnings |
| Adapters | `src/sources/*` | Map each API JSON → `Job` |
| Domain | `src/models.py` | Immutable `Job` |
| Analysis | `src/analysis/skills.py` | Lexicon, matcher, ranked `SkillStat` |
| Chat | `src/chat/handler.py` | Intent routing over cached stats |
| Config | `config.py` | Paths, APIs, fetch limits, region aliases |

There is **no README**, **no git repo at project root**, **no tests**, and **no on-disk job cache**. Data lives only in `st.session_state`.

---

## What works

- Clean split: adapters → `Job` → `SkillMatcher` → chat intents
- Frozen dataclasses, lexicon in JSON (easy to edit)
- Dedup by URL / title+company
- Chat can override region from text (`hk`, `usa`)

---

## Critical bugs

1. **USA and Global are almost the same dataset.**  
   Jobicy/Remotive tag `Job.regions`, but `refresh_region` never filters on it. Refreshing USA or Global dumps the full remote pool into that region.

2. **TTL is dead.**  
   `cache_ttl_hours = 6` and `cache_is_fresh()` exist; UI never uses them. Browser refresh = empty cache. `res/data` is unused.

3. **Relevance fallback dumps noise.**  
   If fewer than 10 title/tag hits, *all* jobs are kept. Descriptions are ignored.

4. **Skill aliases over-match.**  
   `ml`, `cv`, `dl`, `express`, `spring`, `oracle`, `android`, `spark` fire on common words. Matcher is built twice (refresh + chat global).

5. **Jooble errors are silent.**  
   Exceptions become `[]`; HK with a bad key looks like “no jobs.” Jooble also skips `http_headers()`.

6. **Compare ignores the prompt.**  
   `compare hk vs usa` compares every cached region, not the named pair. Chat `top_n=15` ignores `settings.display.top_n`.

---

## Structure debt

- No README, `.gitignore`, `.env.example`, tests, git
- Empty stubs: `src/pages`, `src/utils`, unused `res/images`
- Jobicy ≈ Remotive copy; source counts computed twice
- `Job.regions`, `DataConfig`, `date_format`, path fields unused

---

## Phased plan

### Phase 1 — Data correctness (do first)

This is the only work that changes what the charts mean.

**Region filter after merge**

- In `src/fetch.py`, keep remote jobs only if `region in job.regions` when target is USA; keep all remotes for Global (or document Global = worldwide remote).
- Optionally skip Jooble location for Global if remotes-only is intended.

**Relevance**

- Scan title + tags + first N chars of description.
- Drop the “if <10 keep everything” fallback, or raise the bar and surface a warning instead.
- Invalidate `_RELEVANCE_CACHE` when `keywords.json` mtime changes.

**Skill matching**

- Drop or length-gate dangerous aliases (`ml`, `cv`, `dl`, `express`, `spring`, `oracle`).
- Require word boundaries + optional title-weighting (title hit counts more than body).
- Build `SkillMatcher` once; pass it into `compute_stats` and chat.

**Fetch reliability**

- Shared `get_json` / `post_json` in `src/sources/base.py` with status, timeout, and a short error string (not just `[]`).
- Jooble uses the same headers; bubble per-source warnings to the sidebar.

### Phase 2 — Architecture cleanup

- Delete unused `src/pages`, `src/utils`, `res/images` (keep `res/data` for cache).
- Wire `cache_is_fresh` in `_refresh`: skip network if TTL valid; show “cached / stale” in sidebar.
- Persist `res/data/{region}.json` (jobs + fetched_at) so a new session hydrates without hitting APIs.
- Deduplicate Jobicy/Remotive: shared `_usa_region(text)` + `_safe_get`.
- Honor `settings.display.top_n` everywhere; parse compare targets from the prompt.
- Add root `.gitignore` (`.env`, `.venv`, `__pycache__`, `res/data/*.json`), `.env.example`, short README (run, key, example prompts).

### Phase 3 — UX / product

- Auto-load last cache on startup; “Refresh” only when stale or forced.
- Sidebar: last fetch time, TTL countdown, per-source errors.
- Chat: suggested chips (`top skills`, `python`, `compare hk vs usa`, `help`); cap history.
- Dashboard above chat: top-10 bar + category breakdown (reuse `SkillStat.category`).
- Compare: named pair only; show % not just counts so HK vs USA volumes are fair.

### Phase 4 — Hardening (after 1–3)

- Tests: relevance, dedupe, region filter, alias false-positives, chat intents (fixture jobs, no live APIs).
- Pin deps (`requirements.txt` exact or lockfile).
- Optional: parallel source fetches; Jooble query trim if rate-limited.

---

## Suggested file touch list

| File | Change |
|---|---|
| `src/fetch.py` | Filter by `job.regions`, relevance, persist/load cache, better warnings |
| `src/app.py` | TTL, hydrate from disk, sidebar age/errors, chips |
| `src/analysis/skills.py` | Safer aliases, shared matcher |
| `src/chat/handler.py` | Parse compare pair, use `top_n`, shared matcher |
| `src/sources/base.py` | Shared HTTP + USA regex |
| `src/sources/*.py` | Use shared HTTP; return errors |
| `res/config/skills.json` | Tighten aliases |
| new: `.gitignore`, `.env.example`, `README.md`, `tests/` | Hygiene |

---

## Out of scope (unless requested)

LLM chat, extra job boards, auth, Docker, multipage Streamlit. Keep it a local rule-based app.

---

## Priority

Phase 1 first. Phases 2–3 make it usable day to day. Phase 4 locks the behavior in.
