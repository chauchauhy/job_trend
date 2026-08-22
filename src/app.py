import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import time

import pandas as pd
import streamlit as st

from config import REGIONS, settings
from src.analysis.skills import compute_stats, top_skills
from src.chat.handler import respond
from src.fetch import cache_is_fresh, load_cached, refresh_region, source_counts

MAX_HISTORY = 50

_CHIPS = ("top skills", "python", "how many jobs", "help")


def run() -> None:
    st.set_page_config(
        page_title=settings.app.title,
        page_icon=settings.app.page_icon,
        layout=settings.app.layout,
    )
    _init_state()
    _render_sidebar()
    st.title(settings.app.title)
    st.caption(
        "Rule-based skill-trend explorer over free job APIs "
        "(JSearch / Jobicy / Remotive / RemoteOK). "
        "Ask things like **top skills**, **python**, or **compare hk vs usa**."
    )
    _render_dashboard()
    _render_chat()


def _config_changed_since(fetched_at: float | None) -> bool:
    if fetched_at is None:
        return False
    candidates = (
        settings.paths.root / ".env",
        settings.paths.config / "skills.json",
        settings.paths.config / "keywords.json",
    )
    return any(path.exists() and path.stat().st_mtime > fetched_at for path in candidates)


def _is_fresh(fetched_at: float | None) -> bool:
    return cache_is_fresh(fetched_at) and not _config_changed_since(fetched_at)


def _init_state() -> None:
    if "region" not in st.session_state:
        st.session_state.region = next(iter(REGIONS))
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if not st.session_state.get("_hydrated"):
        for region in REGIONS:
            cached = load_cached(region)
            if cached is not None:
                jobs, fetched_at = cached
                st.session_state[region] = jobs
                st.session_state[f"_fetched_{region}"] = fetched_at
                st.session_state[f"_stats_{region}"] = compute_stats(jobs) if jobs else []
        st.session_state._hydrated = True


def _refresh(region: str) -> None:
    with st.spinner(f"Fetching {region} jobs from APIs..."):
        jobs, warnings = refresh_region(region)
    st.session_state[region] = jobs
    st.session_state[f"_fetched_{region}"] = time.time()
    st.session_state[f"_stats_{region}"] = compute_stats(jobs) if jobs else []
    st.session_state[f"_warn_{region}"] = warnings


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("Controls")
        region = st.radio("Region", list(REGIONS), key="region")

        if st.button("Refresh jobs", type="primary", use_container_width=True):
            _refresh(region)

        if not settings.api.jsearch_api_key:
            st.warning("No `JSEARCH_API_KEY` in `.env` — Hong Kong will stay empty.")

        jobs = st.session_state.get(region)
        if jobs is None:
            st.info("No data yet — hit **Refresh jobs**.")
        elif len(jobs) == 0:
            st.error("0 jobs cached. Check warnings below.")
        else:
            fetched_at = st.session_state.get(f"_fetched_{region}")
            age_min = int((time.time() - fetched_at) / 60) if fetched_at else 0
            badge = "🟢 fresh" if _is_fresh(fetched_at) else "🟠 stale"
            note = " · config changed — refresh" if _config_changed_since(fetched_at) else ""
            st.metric(
                "Jobs cached",
                len(jobs),
                help=f"fetched {age_min} min ago · TTL {settings.fetch.cache_ttl_hours}h",
            )
            st.caption(f"{badge} · fetched {age_min} min ago{note}")
            counts = source_counts(jobs)
            st.write({source: int(n) for source, n in counts.items()})
            stats = st.session_state.get(f"_stats_{region}") or []
            if stats:
                st.caption("Top 5 preview")
                for s in stats[:5]:
                    st.write(f"{s.name} · {s.count}")

        for warning in st.session_state.get(f"_warn_{region}") or []:
            st.warning(warning)

        st.divider()
        st.caption(
            "Sources: [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) · "
            "[Jobicy](https://jobicy.com) · "
            "[Remotive](https://remotive.com) · "
            "[RemoteOK](https://remoteok.com). "
            "Remote boards enrich USA/Global; HK uses JSearch."
        )


def _render_dashboard() -> None:
    region = st.session_state.region
    jobs = st.session_state.get(region)
    stats = st.session_state.get(f"_stats_{region}")
    if not jobs or not stats:
        return
    st.subheader(f"Dashboard · {region}")
    frame = pd.DataFrame(
        {
            "skill": [s.name for s in stats],
            "category": [s.category for s in stats],
            "jobs": [s.count for s in stats],
        }
    )
    top_stats = top_skills(stats)
    top_frame = pd.DataFrame(
        {"skill": [s.name for s in top_stats], "jobs": [s.count for s in top_stats]}
    ).set_index("skill")
    col_chart, col_cat = st.columns([3, 2])
    with col_chart:
        st.bar_chart(top_frame["jobs"], height=320)
    with col_cat:
        by_category = (
            frame.groupby("category")["jobs"].sum().sort_values(ascending=False).to_frame("mentions")
        )
        st.dataframe(by_category, use_container_width=True)
    with st.expander("Full skill table"):
        st.dataframe(frame, use_container_width=True, hide_index=True)


def _render_chat() -> None:
    for role, text, df in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(text)
            if df is not None and not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                if {"skill", "jobs"}.issubset(df.columns):
                    st.bar_chart(df.set_index("skill")["jobs"], height=320)

    chip_cols = st.columns(len(_CHIPS))
    clicked_chip: str | None = None
    for col, chip in zip(chip_cols, _CHIPS):
        if col.button(chip, use_container_width=True):
            clicked_chip = chip

    prompt = clicked_chip or st.chat_input("e.g. what's hot here?")
    if not prompt:
        return
    st.session_state.messages.append(("user", prompt, None))
    reply_text, reply_df = respond(prompt, st.session_state.region, st.session_state)
    st.session_state.messages.append(("assistant", reply_text, reply_df))
    st.session_state.messages = st.session_state.messages[-MAX_HISTORY:]
    st.rerun()
