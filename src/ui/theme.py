import html

import streamlit as st

REGION_DOTS: dict[str, str] = {
    "Hong Kong": "#E5484D",
    "USA": "#3E63DD",
    "Global": "#30A46C",
}

CATEGORY_COLORS: dict[str, str] = {
    "languages": "#6366F1",
    "frameworks_web": "#0EA5E9",
    "cloud_devops": "#10B981",
    "data_ai": "#8B5CF6",
    "databases": "#F59E0B",
    "mobile": "#EC4899",
    "practices": "#64748B",
}

LIGHT_PALETTE: dict[str, str] = {
    "canvas": "#FAFAFA",
    "card": "#FFFFFF",
    "card2": "#F4F4F5",
    "border": "#EAEAEA",
    "ink": "#171717",
    "muted": "#666666",
    "accent": "#0070F3",
    "up": "#0070F3",
    "signal": "#E00000",
    "shadow": "0 4px 14px 0 rgba(0,0,0,.05)",
    "btn_bg": "#000000",
    "btn_fg": "#FFFFFF",
}

DARK_PALETTE: dict[str, str] = {
    "canvas": "#0A0A0A",
    "card": "#111112",
    "card2": "#1B1B1F",
    "border": "#2E2E33",
    "ink": "#EDEDED",
    "muted": "#A1A1AA",
    "accent": "#3291FF",
    "up": "#3291FF",
    "signal": "#FF6369",
    "shadow": "0 0 0 1px rgba(255,255,255,.03)",
    "btn_bg": "#FFFFFF",
    "btn_fg": "#0A0A0A",
}

_CURRENT = LIGHT_PALETTE


def palette() -> dict[str, str]:
    return _CURRENT


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, "#64748B")


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def inject_theme(region: str, dark: bool = False) -> None:
    global _CURRENT
    _CURRENT = DARK_PALETTE if dark else LIGHT_PALETTE
    css = _CSS
    for key, value in {**_CURRENT, "region": REGION_DOTS.get(region, REGION_DOTS["Global"])}.items():
        css = css.replace(f"__{key}__", value)
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


def demand_chart(stats: list, limit: int = 12, height: int | None = None) -> None:
    import altair as alt
    import pandas as pd

    pal = _CURRENT
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
    palette_values = list(CATEGORY_COLORS.values())
    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadius=0, cornerRadiusEnd=4, height=14)
        .encode(
            x=alt.X(
                "jobs:Q",
                title=None,
                axis=alt.Axis(grid=False, labelColor=pal["muted"], tickColor=pal["border"], domainColor=pal["border"], labelFontSize=11),
            ),
            y=alt.Y(
                "skill:N",
                sort=order,
                title=None,
                axis=alt.Axis(labelColor=pal["ink"], labelFontSize=12.5, ticks=False, domain=False, labelFontWeight=500),
            ),
            color=alt.Color("category:N", scale=alt.Scale(domain=domain, range=palette_values), legend=None),
            tooltip=[
                alt.Tooltip("skill:N", title="skill"),
                alt.Tooltip("category:N", title="category"),
                alt.Tooltip("jobs:Q", title="listings"),
                alt.Tooltip("share:N", title="share"),
            ],
        )
        .configure(background=pal["card"])
        .configure_view(stroke=None)
        .properties(height=height or 27 * len(top) + 18)
    )
    st.altair_chart(chart, width="stretch")


def category_donut(stats: list, height: int | None = None) -> None:
    import altair as alt
    import pandas as pd

    pal = _CURRENT
    totals: dict[str, int] = {}
    for s in stats:
        totals[s.category] = totals.get(s.category, 0) + s.count
    frame = pd.DataFrame({"category": list(totals), "mentions": list(totals.values())})
    chart = (
        alt.Chart(frame)
        .mark_arc(innerRadius=72, outerRadius=98, cornerRadius=3)
        .encode(
            theta=alt.Theta("mentions:Q"),
            color=alt.Color(
                "category:N",
                scale=alt.Scale(domain=list(CATEGORY_COLORS.keys()), range=list(CATEGORY_COLORS.values())),
                legend=alt.Legend(
                    orient="bottom",
                    labelColor=pal["muted"],
                    labelFontSize=11,
                    symbolType="circle",
                    columns=2,
                    padding=8,
                ),
            ),
            tooltip=[alt.Tooltip("category:N", title="category"), alt.Tooltip("mentions:Q", title="mentions")],
        )
        .configure(background=pal["card"])
        .configure_view(stroke=None)
        .properties(height=height or 250)
    )
    st.altair_chart(chart, width="stretch")


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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root{
    --canvas:__canvas__; --card:__card__; --card2:__card2__; --border:__border__;
    --ink:__ink__; --muted:__muted__;
    --accent:__accent__; --up:__up__; --signal:__signal__;
    --shadow:__shadow__; --btn-bg:__btn_bg__; --btn-fg:__btn_fg__;
    --region:__region__;
}
.stApp{background:var(--canvas);color:var(--ink);font-family:'Inter',system-ui,sans-serif;}
header[data-testid="stHeader"]{background:transparent;}
footer{visibility:hidden;}
#MainMenu{visibility:hidden;}
.block-container{padding-top:.9rem;max-width:1440px;}

.brand{display:flex;align-items:center;gap:9px;font-size:16.5px;font-weight:700;color:var(--ink);padding-top:6px;white-space:nowrap;letter-spacing:-0.01em;}
.brand .dot{width:8px;height:8px;border-radius:50%;}
.brand small{color:var(--muted);font-weight:500;font-size:12px;}

.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px;box-shadow:var(--shadow);}
.kpi{min-height:96px;display:flex;flex-direction:column;justify-content:center;border-radius:12px;}
.kpi__label{font-size:10.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);}
.kpi__value{font-size:27px;font-weight:650;line-height:1.15;margin-top:5px;color:var(--ink);letter-spacing:-0.02em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.kpi__sub{font-size:12px;color:var(--muted);margin-top:3px;}

.sec-head{display:flex;align-items:baseline;justify-content:space-between;margin:18px 0 6px;font-weight:600;font-size:14.5px;letter-spacing:-0.01em;}
.sec-note{font-weight:400;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);}

.side-label{font-size:10.5px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin:12px 0 4px;}
.feed-row{display:flex;justify-content:space-between;font-size:13px;padding:3px 0;color:var(--ink);}
.feed-row__num{color:var(--muted);}

.chip{display:inline-block;font-size:10.5px;font-weight:600;letter-spacing:.1em;padding:3px 10px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--muted);}
.chip--up{color:var(--up);border-color:var(--up);}
.chip--signal{color:var(--signal);border-color:var(--signal);}

.warn-line{font-size:12px;color:var(--signal);padding:3px 0;line-height:1.5;}

.msg-user code{font-size:13px;color:var(--ink);background:var(--card2);border:1px solid var(--border);padding:6px 10px;border-radius:10px;display:inline-block;white-space:pre-wrap;}
.bot-rule{height:2px;width:40px;background:var(--ink);border-radius:2px;margin:14px 0 4px;}

[data-testid="stVerticalBlockBorderWrapper"]{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:12px!important;box-shadow:var(--shadow)!important;}
button[kind="primary"]{border-radius:8px !important;font-weight:600 !important;background:var(--btn-bg) !important;border-color:var(--btn-bg) !important;color:var(--btn-fg) !important;}
button[kind="primary"]:hover{opacity:.82;}
button[kind="secondary"], button[kind="secondaryHeader"]{background:var(--card)!important;border-color:var(--border)!important;color:var(--ink)!important;}
[data-testid="stSidebar"]{background:var(--canvas);border-right:none;}
[data-testid="stExpander"], [data-testid="stExpanderDetails"]{background:var(--card);border-color:var(--border);border-radius:12px;}
.stChatInput textarea{background:var(--card2)!important;border:1px solid var(--border)!important;border-radius:10px!important;color:var(--ink)!important;}
hr{border-color:var(--border)!important;}
[data-testid="stSegmentedControl"] *{font-family:'Inter',sans-serif;}
"""
