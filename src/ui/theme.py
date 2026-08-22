import html

import streamlit as st

REGION_DOTS: dict[str, str] = {
    "Hong Kong": "#FF6B6B",
    "USA": "#5B8DEF",
    "Global": "#34D399",
}

CATEGORY_COLORS: dict[str, str] = {
    "languages": "#7DA2FF",
    "frameworks_web": "#FF9E7D",
    "cloud_devops": "#4FD1B5",
    "data_ai": "#C39BFF",
    "databases": "#F2C879",
    "mobile": "#FF8FB1",
    "practices": "#8CA0B8",
}


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, "#8CA0B8")


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def inject_theme(region: str) -> None:
    dot = REGION_DOTS.get(region, REGION_DOTS["Global"])
    css = _CSS.replace("__REGION__", dot)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def brand(region: str) -> None:
    dot = REGION_DOTS.get(region, REGION_DOTS["Global"])
    st.markdown(
        f"""
        <div class="brand">
            <span class="dot" style="background:{dot}"></span>
            JobTrend
            <small>console</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_chip(text: str, tone: str = "neutral") -> None:
    tone_class = {"up": "chip--up", "signal": "chip--signal", "neutral": "chip--neutral"}.get(tone, "chip--neutral")
    st.markdown(f"<span class='chip {tone_class}'>{_esc(text)}</span>", unsafe_allow_html=True)


def kpi_tiles(tiles: list[tuple[str, str, str]]) -> None:
    cols = st.columns(len(tiles))
    for col, (label, value, sub) in zip(cols, tiles):
        col.markdown(
            f"""
            <div class="card kpi">
                <span class="kpi__label">{_esc(label)}</span>
                <span class="kpi__value">{_esc(value)}</span>
                <span class="kpi__sub">{_esc(sub)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def section_title(title: str, note: str = "") -> None:
    note_html = f"<span class='sec-note'>{_esc(note)}</span>" if note else ""
    st.markdown(f"<div class='sec-head'>{_esc(title)}{note_html}</div>", unsafe_allow_html=True)


def demand_chart(stats: list, limit: int = 12) -> None:
    import altair as alt
    import pandas as pd

    top = stats[:limit]
    frame = pd.DataFrame(
        {
            "skill": [s.name for s in top],
            "jobs": [s.count for s in top],
            "share": [f"{s.pct}%" for s in top],
            "category": [s.category for s in top],
        }
    )
    order = frame.sort_values("jobs")["skill"].tolist()
    domain = list(CATEGORY_COLORS.keys())
    palette = list(CATEGORY_COLORS.values())
    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadius=3, height=15)
        .encode(
            x=alt.X(
                "jobs:Q",
                title=None,
                axis=alt.Axis(grid=True, gridColor="#1C2A42", labelColor="#93A4BD", tickColor="#1C2A42", domainColor="#1C2A42"),
            ),
            y=alt.Y("skill:N", sort=order, title=None, axis=alt.Axis(labelColor="#EAF0FA", labelFontSize=12.5, ticks=False, domain=False)),
            color=alt.Color("category:N", scale=alt.Scale(domain=domain, range=palette), legend=None),
            tooltip=[
                alt.Tooltip("skill:N", title="skill"),
                alt.Tooltip("category:N", title="category"),
                alt.Tooltip("jobs:Q", title="listings"),
                alt.Tooltip("share:N", title="share"),
            ],
        )
        .configure(background="#131C2E")
        .configure_view(stroke=None)
        .properties(height=27 * len(top) + 18)
    )
    st.altair_chart(chart, use_container_width=True)


def category_donut(stats: list) -> None:
    import altair as alt
    import pandas as pd

    totals: dict[str, int] = {}
    for s in stats:
        totals[s.category] = totals.get(s.category, 0) + s.count
    frame = pd.DataFrame({"category": list(totals), "mentions": list(totals.values())})
    domain = [c for c in CATEGORY_COLORS if c in totals]
    palette = [CATEGORY_COLORS[c] for c in domain]
    chart = (
        alt.Chart(frame)
        .mark_arc(innerRadius=58, outerRadius=105, cornerRadius=3)
        .encode(
            theta=alt.Theta("mentions:Q"),
            color=alt.Color(
                "category:N",
                scale=alt.Scale(domain=list(CATEGORY_COLORS.keys()), range=list(CATEGORY_COLORS.values())),
                legend=alt.Legend(orient="bottom", labelColor="#93A4BD", labelFontSize=11.5, symbolType="circle", columns=2),
            ),
            tooltip=[alt.Tooltip("category:N", title="category"), alt.Tooltip("mentions:Q", title="mentions")],
        )
        .configure(background="#131C2E")
        .configure_view(stroke=None)
        .properties(height=250)
    )
    st.altair_chart(chart, use_container_width=True)


def side_label(label: str) -> None:
    st.markdown(f"<div class='side-label'>{_esc(label)}</div>", unsafe_allow_html=True)


def feed_row(left: str, right: str) -> None:
    st.markdown(
        f"<div class='feed-row'><span>{_esc(left)}</span><span class='feed-row__num'>{_esc(right)}</span></div>",
        unsafe_allow_html=True,
    )


def warn_line(text: str) -> None:
    st.markdown(f"<div class='warn-line'>⌁ {_esc(text)}</div>", unsafe_allow_html=True)


def user_line(text: str) -> None:
    st.markdown(f"<div class='msg-user'><code>&gt; {_esc(text)}</code></div>", unsafe_allow_html=True)


def assistant_rule() -> None:
    st.markdown("<div class='bot-rule'></div>", unsafe_allow_html=True)


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

:root{
    --canvas:#0C1220; --card:#131C2E; --card2:#18243A; --border:#22304A;
    --ink:#EAF0FA; --muted:#93A4BD; --primary:#6C8CFF;
    --up:#34D399; --signal:#F87171; --region:__REGION__;
}
.stApp{background:var(--canvas);color:var(--ink);font-family:'Inter',system-ui,sans-serif;}
header[data-testid="stHeader"]{background:transparent;}
footer{visibility:hidden;}
#MainMenu{visibility:hidden;}
.block-container{padding-top:.9rem;max-width:1440px;}

.brand{display:flex;align-items:center;gap:9px;font-size:16.5px;font-weight:650;color:var(--ink);padding-top:6px;white-space:nowrap;}
.brand .dot{width:9px;height:9px;border-radius:50%;box-shadow:0 0 10px currentColor;background-clip:padding-box;}
.brand small{color:var(--muted);font-weight:500;font-size:12px;}

.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px 16px;}
.kpi{min-height:96px;display:flex;flex-direction:column;justify-content:center;}
.kpi__label{font-size:10.5px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);}
.kpi__value{font-family:'IBM Plex Mono',monospace;font-size:29px;font-weight:600;line-height:1.15;margin-top:5px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.kpi__sub{font-size:12px;color:var(--muted);margin-top:3px;}

.sec-head{display:flex;align-items:baseline;justify-content:space-between;margin:18px 0 4px;font-weight:600;font-size:14.5px;}
.sec-note{font-family:'IBM Plex Mono',monospace;font-weight:400;font-size:11.5px;letter-spacing:.1em;color:var(--muted);}

.side-label{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin:12px 0 4px;}
.feed-row{display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:12.5px;padding:2px 0;color:var(--ink);}
.feed-row__num{color:var(--muted);}

.chip{display:inline-block;font-family:'IBM Plex Mono',monospace;font-size:10.5px;font-weight:600;letter-spacing:.12em;padding:3px 10px;border-radius:999px;border:1.5px solid var(--border);color:var(--muted);}
.chip--up{color:var(--up);border-color:var(--up);}
.chip--signal{color:var(--signal);border-color:var(--signal);}

.warn-line{font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:var(--signal);padding:3px 0;line-height:1.45;}

.msg-user code{font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--ink);background:var(--card2);border:1px solid var(--border);padding:6px 10px;border-radius:8px;display:inline-block;white-space:pre-wrap;}
.bot-rule{height:2px;width:44px;background:var(--primary);border-radius:2px;margin:14px 0 4px;}

[data-testid="stVerticalBlockBorderWrapper"]{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:14px!important;}
button[kind="primary"]{border-radius:8px !important;font-weight:600 !important;}
[data-testid="stSidebar"]{background:#0A0F1B;border-right:1px solid var(--border);}
[data-testid="stExpander"], [data-testid="stExpanderDetails"]{background:var(--card);border-color:var(--border);border-radius:12px;}
.stChatInput textarea{background:var(--card2)!important;border:1px solid var(--border)!important;border-radius:10px!important;}
"""
