# Job Trend — Sequence Diagrams

## 1. Startup + Refresh pipeline

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant UI as src/app.py (Streamlit)
    participant F as src/fetch.py
    participant S as src/sources/*
    participant API as External APIs
    participant K as res/config/*.json
    participant D as res/data/{region}.json
    participant A as src/analysis/skills.py
    participant ST as st.session_state

    U->>UI: open app / pick region / Refresh jobs
    UI->>D: load_cached(region)
    alt cache exists on disk
        D-->>UI: (jobs, fetched_at)
        UI->>ST: hydrate jobs + fetched_at + compute_stats
    end
    Note over UI: badge = fresh if TTL ok AND .env/config mtimes unchanged

    U->>UI: click Refresh jobs (always fetches)
    UI->>F: refresh_region(region)
    F->>K: load keywords.json (mtime-keyed regex cache)

    rect rgb(235, 245, 255)
        note right of F: JSearch — regions Hong Kong / USA, needs x-api-key
        F->>S: jsearch.fetch(keywords, region)
        loop keyword × page (≤2 pages)
            S->>API: GET api.openwebninja.com/jsearch/search<br/>query=keyword[+suffix] [&country=us]<br/>x-api-key
            API-->>S: data[] | HTTP 429 → sleep 2.5s retry once
            S->>S: strip_html → Job(regions={region})
            S->>S: sleep 1.1s (throttle)
        end
        S-->>F: ([Jobs], error?)
    end

    rect rgb(235, 255, 240)
        note right of F: Remote boards — USA / Global only, no keys
        par Jobicy
            F->>S: jobicy.fetch()
            S->>API: GET jobicy.com/api/v2/remote-jobs
            API-->>S: jobs[]
        and Remotive
            F->>S: remotive.fetch()
            S->>API: GET remotive.com/api/remote-jobs?category=software-dev
            API-->>S: jobs[]
        and RemoteOK
            F->>S: remoteok.fetch()
            S->>API: GET remoteok.com/api
            API-->>S: list (skip notice element)
        end
        S-->>F: ([Jobs], error?)
    end

    F->>F: merge + dedupe (url | title+company)
    F->>F: region filter (USA keeps USA-tagged only; Global keeps all)
    F->>F: relevance: title+tags hit OR description[:600] hit
    F->>F: sort (jsearch first) + cap 150
    F->>D: save_cache(region, jobs, now)
    F-->>UI: (jobs, warnings[])
    UI->>A: compute_stats(jobs)
    A->>K: load skills.json (categories + aliases)
    A->>A: SkillMatcher word-boundary match<br/>title hits score 2×
    A-->>UI: [SkillStat(name, category, count, pct)]
    UI->>ST: store all + warnings
    UI->>U: sidebar metrics 🟢/🟠, source counts, dashboard chart
```

## 2. Chat question → answer

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant UI as src/app.py
    participant H as src/chat/handler.py
    participant M as SkillMatcher
    participant ST as st.session_state

    U->>UI: chat_input / suggestion chip
    UI->>ST: messages += ("user", text)
    UI->>H: respond(text, default_region, store)

    H->>M: get_matcher() (singleton)
    H->>H: resolve_region(text) — hk/usa/global override?
    alt region not cached
        H-->>UI: "Refresh jobs first"
    end

    switch intent (regex order)
        case help
            H-->>UI: help text
        case compare X vs Y
            H->>ST: _stats_for(X), _stats_for(Y)
            H->>H: top-N each, union rows, counts + % columns
            H-->>UI: markdown + DataFrame
        case how many jobs
            H-->>UI: counts by source
        case top skills / hot stack
            H->>ST: _stats_{region} (compute once if missing)
            H-->>UI: table + df (top_n from settings.display.top_n)
        case known skill name
            H->>M: find_in_text(query)
            H->>ST: lookup_skill(stats)
            H-->>UI: count / % of pool / sample roles
        case unknown but looks like "<x> jobs?"
            H->>H: _guess_skill longest token
            H-->>UI: stat or "doesn't appear"
        else fallback
            H-->>UI: "type help"
        end
    end

    UI->>ST: messages += ("assistant", reply, df?) (cap 50)
    UI->>U: render markdown + dataframe + bar_chart
```
