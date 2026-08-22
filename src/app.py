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
from src.ui.theme import (
    REGION_COLORS,
    bot_rule,
    category_mix,
    dash_head,
    feed_row,
    inject_theme,
    render_masthead,
    render_ticker,
    side_label,
    skill_bars,
    status_chip,
    user_line,
    warn_line,
)

MAX_HISTORY = 50

_CHIPS = ("top skills", "python", "how many jobs", "help")


def run() -> None:
    st.set_page_config(
        page_title=settings.app.title,
        page_icon=settings.app.page_icon,
        layout=settings.app.layout,
    )
    _init_state()
    region = st.session_state.region
    inject_theme(region)
    render_masthead(region)

    stats = st.session_state.get(f"_stats_{region}") or []
    if stats:
        render_ticker(stats)
    else:
        st.markdown("<div class='tape'><div class='tape__track'></div></div>", unsafe_allow_html=True)

    _render_sidebar()
    _render_dashboard(region)
    _render_chat(region)


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
    with st.spinner(f"Pulling the {region} tape…"):
        jobs, warnings = refresh_region(region)
    st.session_state[region] = jobs
    st.session_state[f"_fetched_{region}"] = time.time()
    st.session_state[f"_stats_{region}"] = compute_stats(jobs) if jobs else []
    st.session_state[f"_warn_{region}"] = warnings


def _render_sidebar() -> None:
    with st.sidebar:
        st.segmented_control("Market", list(REGIONS), key="region", label_visibility="collapsed")

        if st.button("Refresh jobs", type="primary", use_container_width=True):
            _refresh(st.session_state.region)

        if not settings.api.jsearch_api_key:
            warn_line("Add JSEARCH_API_KEY to .env to unlock Hong Kong.")

        region = st.session_state.region
        jobs = st.session_state.get(region)

        side_label("Feed")
        if jobs is None:
            st.markdown("<div class='feed-row'><span>no pull yet</span></div>", unsafe_allow_html=True)
        elif len(jobs) == 0:
            warn_line("Last pull returned 0 listings — check notes below.")
        else:
            counts = source_counts(jobs)
            for source, count in counts.most_common():
                feed_row(source, str(int(count)))
            feed_row("total", str(len(jobs)))

        fetched_at = st.session_state.get(f"_fetched_{region}")
        if fetched_at and jobs:
            age_min = int((time.time() - fetched_at) / 60)
            fresh = _is_fresh(fetched_at)
            status_chip("FRESH" if fresh else "STALE", tone="up" if fresh else "signal")
            note = "config changed — re-pull" if _config_changed_since(fetched_at) else f"{age_min} min ago"
            st.markdown(f"<div class='feed-row'><span class='feed-row__num'>{note}</span></div>", unsafe_allow_html=True)

        warnings = st.session_state.get(f"_warn_{region}") or []
        if warnings:
            side_label(f"Notes ({len(warnings)})")
            for warning in warnings:
                warn_line(warning)

        st.divider()
        st.caption(
            "Feeds: [JSearch](https://app.openwebninja.com/api/jsearch) · "
            "[Jobicy](https://jobicy.com) · "
            "[Remotive](https://remotive.com) · "
            "[RemoteOK](https://remoteok.com). "
            "Remote boards cover USA/Global; Hong Kong runs on JSearch."
        )


def _render_dashboard(region: str) -> None:
    jobs = st.session_state.get(region)
    stats = st.session_state.get(f"_stats_{region}") or []

    dash_head(f"Top Skills · {region}", f"{len(jobs) if jobs else 0} LISTINGS")

    if not jobs:
        st.markdown(
            "<div class='cat-mix'>No tape yet — hit <b>Refresh jobs</b> to pull the first batch.</div>",
            unsafe_allow_html=True,
        )
        return
    if not stats:
        return

    skill_bars(stats)
    category_mix(stats)

    with st.expander("Full skill table"):
        frame = pd.DataFrame(
            {
                "skill": [s.name for s in stats],
                "category": [s.category for s in stats],
                "jobs": [s.count for s in stats],
                "%": [s.pct for s in stats],
            }
        )
        st.dataframe(frame, use_container_width=True, hide_index=True)


def _render_chat(region: str) -> None:
    for role, text, df in st.session_state.messages:
        if role == "user":
            user_line(text)
        else:
            bot_rule()
            st.markdown(text)
            if df is not None and not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)

    if not st.session_state.messages and not st.session_state.get(region):
        st.markdown(
            "<div class='cat-mix'>Ask about any skill once a pull exists — try <b>top skills</b>.</div>",
            unsafe_allow_html=True,
        )

    chip_cols = st.columns(len(_CHIPS))
    clicked_chip: str | None = None
    for col, chip in zip(chip_cols, _CHIPS):
        if col.button(chip, use_container_width=True):
            clicked_chip = chip

    prompt = clicked_chip or st.chat_input("Ask the tape…")
    if not prompt:
        return
    st.session_state.messages.append(("user", prompt, None))
    reply_text, reply_df = respond(prompt, region, st.session_state)
    st.session_state.messages.append(("assistant", reply_text, reply_df))
    st.session_state.messages = st.session_state.messages[-MAX_HISTORY:]
    st.rerun()
