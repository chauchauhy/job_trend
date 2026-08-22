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
    assistant_rule,
    brand,
    category_donut,
    demand_chart,
    feed_row,
    inject_theme,
    section_title,
    side_label,
    status_chip,
    summary_strip,
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
    jobs = st.session_state.get(region)
    stats = st.session_state.get(f"_stats_{region}") or []

    _topbar(region)
    _render_sidebar()
    _summary_strip(region, jobs, stats)
    _chart_grid(jobs, stats)
    _assistant(region)


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
                pulled, fetched_at = cached
                st.session_state[region] = pulled
                st.session_state[f"_fetched_{region}"] = fetched_at
                st.session_state[f"_stats_{region}"] = compute_stats(pulled) if pulled else []
        st.session_state._hydrated = True


def _refresh(region: str) -> None:
    with st.spinner(f"Pulling {region} listings…"):
        jobs, warnings = refresh_region(region)
    st.session_state[region] = jobs
    st.session_state[f"_fetched_{region}"] = time.time()
    st.session_state[f"_stats_{region}"] = compute_stats(jobs) if jobs else []
    st.session_state[f"_warn_{region}"] = warnings


def _topbar(region: str) -> None:
    left, mid, right = st.columns([1.0, 1.4, 1.0], vertical_alignment="center")
    with left:
        brand(region)
    with mid:
        st.segmented_control("Market", list(REGIONS), key="region", label_visibility="collapsed")
    with right:
        button_col, chip_col = right.columns([1.1, 1.0])
        if button_col.button("⟳ Refresh", type="primary", width="stretch"):
            _refresh(st.session_state.region)
        fetched_at = st.session_state.get(f"_fetched_{region}")
        jobs = st.session_state.get(region)
        if fetched_at and jobs:
            fresh = _is_fresh(fetched_at)
            chip_col.markdown(
                status_chip_inline("FRESH" if fresh else "STALE", "up" if fresh else "signal"),
                unsafe_allow_html=True,
            )


def status_chip_inline(text: str, tone: str) -> str:
    tone_class = {"up": "chip--up", "signal": "chip--signal"}.get(tone, "")
    from src.ui.theme import _esc

    return f"<div style='text-align:right;padding-top:6px;'><span class='chip {tone_class}'>{_esc(text)}</span></div>"


def _render_sidebar() -> None:
    with st.sidebar:
        region = st.session_state.region

        if not settings.api.jsearch_api_key:
            warn_line("Add JSEARCH_API_KEY to .env to unlock Hong Kong.")

        jobs = st.session_state.get(region)
        side_label("Feed")
        if jobs is None:
            feed_row("status", "no pull yet")
        elif len(jobs) == 0:
            warn_line("Last pull returned 0 listings — see notes.")
        else:
            counts = source_counts(jobs)
            for source, count in counts.most_common():
                feed_row(source, str(int(count)))
            feed_row("total", str(len(jobs)))

            fetched_at = st.session_state.get(f"_fetched_{region}")
            age_min = int((time.time() - fetched_at) / 60) if fetched_at else 0
            note = "config changed — re-pull" if _config_changed_since(fetched_at) else f"{age_min} min ago"
            feed_row("pulled", note)

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


def _summary_strip(region: str, jobs: list | None, stats: list) -> None:
    items: list[tuple[str, str]] = []
    if jobs is None:
        items.append(("status", "no pull yet"))
    elif len(jobs) == 0:
        items.append(("listings", "0 — see notes"))
    else:
        items.append(("listings analyzed", str(len(jobs))))
        if stats:
            lead = stats[0]
            items.append(("top skill", f"{lead.name} ({lead.pct}%)"))
        items.append(("skills tracked", str(len(stats))))
        fetched_at = st.session_state.get(f"_fetched_{region}")
        if fetched_at:
            age_min = int((time.time() - fetched_at) / 60)
            note = "just now" if age_min < 1 else f"{age_min} min ago"
            items.append(("pulled", note))
    section_title(f"{region} market")
    summary_strip(items)


def _chart_grid(jobs: list | None, stats: list) -> None:
    shared_height = 30 * min(len(stats), 14) + 24 if stats else 300
    left, right = st.columns([2.0, 1.0], gap="medium")
    with left:
        section_title("Skill demand", "TOP 14 BY MENTIONS")
        if stats:
            with st.container(border=True):
                demand_chart(stats, height=shared_height)
        else:
            st.markdown(
                "<div class='card' style='color:#A1A1AA'>No data yet — hit <b>⟳ Refresh</b> to pull the first batch.</div>",
                unsafe_allow_html=True,
            )
    with right:
        section_title("Category mix")
        if stats:
            with st.container(border=True):
                category_donut(stats, height=shared_height)
        else:
            st.markdown("<div class='card' style='color:#A1A1AA'>Waiting on data.</div>", unsafe_allow_html=True)

    if stats:
        with st.expander("Full skill table"):
            frame = pd.DataFrame(
                {
                    "skill": [s.name for s in stats],
                    "category": [s.category for s in stats],
                    "jobs": [s.count for s in stats],
                    "%": [s.pct for s in stats],
                }
            )
            st.dataframe(frame, width="stretch", hide_index=True)


def _assistant(region: str) -> None:
    section_title("Assistant", "RULE-BASED · NO LLM")
    with st.container(border=True):
        for role, text, df in st.session_state.messages:
            if role == "user":
                user_line(text)
            else:
                assistant_rule()
                st.markdown(text)
                if df is not None and not df.empty:
                    st.dataframe(df, width="stretch", hide_index=True)

        if not st.session_state.messages and not st.session_state.get(region):
            st.caption("Pull a market first, then ask about any skill on the tape.")

        chip_cols = st.columns(len(_CHIPS))
        clicked_chip: str | None = None
        for col, chip in zip(chip_cols, _CHIPS):
            if col.button(chip, key=f"chip-{chip}", width="stretch"):
                clicked_chip = chip

        prompt = clicked_chip or st.chat_input("Ask about a skill…")
        if not prompt:
            return
        st.session_state.messages.append(("user", prompt, None))
        reply_text, reply_df = respond(prompt, region, st.session_state)
        st.session_state.messages.append(("assistant", reply_text, reply_df))
        st.session_state.messages = st.session_state.messages[-MAX_HISTORY:]
        st.rerun()
