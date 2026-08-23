import html

import streamlit as st

REGION_DOTS: dict[str, str] = {
    "Hong Kong": "#F87171",
    "USA": "#60A5FA",
    "Global": "#34D399",
}

CATEGORY_COLORS: dict[str, str] = {
    "languages": "#818CF8",
    "frameworks_web": "#38BDF8",
    "cloud_devops": "#34D399",
    "data_ai": "#A78BFA",
    "databases": "#FBBF24",
    "mobile": "#F472B6",
    "practices": "#94A3B8",
}

INK = "#FAFAFA"
MUTED = "#A1A1AA"
BORDER = "#27272A"
CARD = "#121214"
CANVAS = "#09090B"

_PALETTE = {
    "canvas": CANVAS,
    "card": CARD,
    "card2": "#1C1C1F",
    "border": BORDER,
    "ink": INK,
    "muted": MUTED,
    "accent": "#3B82F6",
    "up": "#3B82F6",
    "signal": "#F87171",
    "btn_bg": "#FAFAFA",
    "btn_fg": "#09090B",
}


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, "#94A3B8")


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def inject_theme(region: str) -> None:
    css = _CSS
    for key, value in {**_PALETTE, "region": REGION_DOTS.get(region, REGION_DOTS["Global"])}.items():
        css = css.replace(f"__{key}__", value)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def brand(region: str, version: str = "") -> None:
    dot = REGION_DOTS.get(region, REGION_DOTS["Global"])
    version_html = f'<span class="beta">{_esc(version)}</span>' if version else ""
    st.markdown(
        f"""
        <div class="brand">
            <span class="dot" style="background:{dot}"></span>
            JobTrend
            <small>console</small>
            {version_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_chip(text: str, tone: str = "neutral") -> None:
    tone_class = {"up": "chip--up", "signal": "chip--signal", "neutral": "chip--neutral"}.get(tone, "chip--neutral")
    st.markdown(f"<span class='chip {tone_class}'>{_esc(text)}</span>", unsafe_allow_html=True)


def summary_strip(items: list[tuple[str, str]]) -> None:
    parts = "".join(
        f"<span class='sum__item'>{_esc(label)}&nbsp;<b>{_esc(value)}</b></span>"
        for label, value in items
    )
    st.markdown(f"<div class='summary-strip'>{parts}</div>", unsafe_allow_html=True)


def section_title(title: str, note: str = "") -> None:
    note_html = f"<span class='sec-note'>{_esc(note)}</span>" if note else ""
    st.markdown(f"<div class='sec-head'>{_esc(title)}{note_html}</div>", unsafe_allow_html=True)


def demand_chart(
    stats: list, limit: int = 14, height: int | None = None, owned: list[str] | None = None
) -> None:
    import altair as alt
    import pandas as pd

    owned_set = set(owned or [])
    top = stats[:limit]
    frame = pd.DataFrame(
        {
            "skill": [f"{s.name} ✓" if s.name in owned_set else s.name for s in top],
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
        .mark_bar(cornerRadius=0, cornerRadiusEnd=3, height=16)
        .encode(
            x=alt.X(
                "jobs:Q",
                title=None,
                axis=alt.Axis(
                    grid=True,
                    gridColor=BORDER,
                    gridDash=[2, 4],
                    gridOpacity=0.7,
                    labelColor=MUTED,
                    tickColor="transparent",
                    domainColor="transparent",
                    labelFontSize=11,
                ),
            ),
            y=alt.Y(
                "skill:N",
                sort=order,
                title=None,
                axis=alt.Axis(labelColor=INK, labelFontSize=13, ticks=False, domain=False, labelFontWeight=600),
            ),
            color=alt.Color("category:N", scale=alt.Scale(domain=domain, range=palette_values), legend=None),
            tooltip=[
                alt.Tooltip("skill:N", title="skill"),
                alt.Tooltip("category:N", title="category"),
                alt.Tooltip("jobs:Q", title="listings"),
                alt.Tooltip("share:N", title="share"),
            ],
        )
        .configure(background="transparent")
        .configure_view(stroke=None)
        .properties(height=height or 30 * len(top) + 24)
    )
    st.altair_chart(chart, width="stretch")


def category_donut(stats: list, height: int | None = None) -> None:
    import altair as alt
    import pandas as pd

    totals: dict[str, int] = {}
    for s in stats:
        totals[s.category] = totals.get(s.category, 0) + s.count
    frame = pd.DataFrame({"category": list(totals), "mentions": list(totals.values())})
    chart = (
        alt.Chart(frame)
        .mark_arc(innerRadius=78, outerRadius=104, cornerRadius=3)
        .encode(
            theta=alt.Theta("mentions:Q"),
            color=alt.Color(
                "category:N",
                scale=alt.Scale(domain=list(CATEGORY_COLORS.keys()), range=list(CATEGORY_COLORS.values())),
                legend=alt.Legend(
                    orient="bottom",
                    labelColor=MUTED,
                    labelFontSize=11.5,
                    symbolType="circle",
                    columns=2,
                    padding=10,
                ),
            ),
            tooltip=[alt.Tooltip("category:N", title="category"), alt.Tooltip("mentions:Q", title="mentions")],
        )
        .configure(background="transparent")
        .configure_view(stroke=None)
        .properties(height=height or 300)
    )
    st.altair_chart(chart, width="stretch")


def trend_chart(snapshots: list[dict], selected: list[str], category_of: dict[str, str]) -> None:
    import altair as alt
    import pandas as pd

    rows = []
    for snap in snapshots:
        total = snap.get("total") or 0
        skills = snap.get("skills", {})
        ts = pd.to_datetime(snap["ts"], unit="s")
        for name in selected:
            count = skills.get(name, 0)
            rows.append(
                {
                    "ts": ts,
                    "skill": name,
                    "pct": round(count / total * 100, 1) if total else 0.0,
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.caption("No data for the selected skills yet.")
        return
    domain: list[str] = []
    palette: list[str] = []
    fallback = ("#F97316", "#22D3EE", "#4ADE80", "#E879F9", "#FACC15")
    used: set[str] = set()
    next_fallback = 0
    for name in selected:
        color = CATEGORY_COLORS.get(category_of.get(name, ""), "")
        if not color or color in used:
            while next_fallback < len(fallback) and fallback[next_fallback] in used:
                next_fallback += 1
            color = fallback[next_fallback] if next_fallback < len(fallback) else MUTED
            next_fallback += 1
        used.add(color)
        domain.append(name)
        palette.append(color)
    chart = (
        alt.Chart(frame)
        .mark_line(point=alt.OverlayMarkDef(size=40), strokeWidth=2)
        .encode(
            x=alt.X(
                "ts:T",
                title=None,
                axis=alt.Axis(
                    grid=True,
                    gridColor=BORDER,
                    gridDash=[2, 4],
                    gridOpacity=0.7,
                    labelColor=MUTED,
                    tickColor="transparent",
                    domainColor="transparent",
                    labelFontSize=11,
                ),
            ),
            y=alt.Y(
                "pct:Q",
                title=None,
                axis=alt.Axis(
                    grid=True,
                    gridColor=BORDER,
                    gridDash=[2, 4],
                    gridOpacity=0.7,
                    labelColor=MUTED,
                    tickColor="transparent",
                    domainColor="transparent",
                    labelFontSize=11,
                ),
            ),
            color=alt.Color(
                "skill:N",
                scale=alt.Scale(domain=domain, range=palette),
                legend=alt.Legend(orient="bottom", labelColor=MUTED, labelFontSize=11.5, columns=4, padding=8),
            ),
            tooltip=[
                alt.Tooltip("skill:N", title="skill"),
                alt.Tooltip("yearmonthdate(ts):T", title="pulled"),
                alt.Tooltip("pct:Q", title="% of listings", format=".1f"),
            ],
        )
        .configure(background="transparent")
        .configure_view(stroke=None)
        .properties(height=280)
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
    --canvas:#09090B; --card:#121214; --card2:#1C1C1F; --border:#27272A;
    --ink:#FAFAFA; --muted:#A1A1AA;
    --accent:#3B82F6; --up:#3B82F6; --signal:#F87171;
    --btn-bg:#FAFAFA; --btn-fg:#09090B;
    --region:__region__;
}
.stApp{background:var(--canvas);color:var(--ink);font-family:'Inter',system-ui,sans-serif;}
header[data-testid="stHeader"]{background:transparent;}
footer{visibility:hidden;}
#MainMenu{visibility:hidden;}
.block-container{padding-top:.9rem;max-width:1440px;}

.brand{display:flex;align-items:center;gap:9px;font-size:16.5px;font-weight:700;color:var(--ink);padding-top:6px;white-space:nowrap;letter-spacing:-0.01em;}
.brand .dot{width:8px;height:8px;border-radius:50%;box-shadow:0 0 12px currentColor;}
.brand small{color:var(--muted);font-weight:500;font-size:12px;}
.brand .beta{font-size:9.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);border:1px solid var(--accent);border-radius:999px;padding:1px 7px;margin-left:-3px;}

.summary-strip{display:flex;flex-wrap:wrap;gap:8px 26px;align-items:center;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:11px 18px;margin-bottom:14px;}
.sum__item{font-size:13px;color:var(--muted);}
.sum__item b{color:var(--ink);font-weight:650;letter-spacing:-0.01em;}

.sec-head{display:flex;align-items:baseline;justify-content:space-between;margin:18px 0 6px;font-weight:600;font-size:14.5px;letter-spacing:-0.01em;}
.sec-note{font-weight:400;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);}

.side-label{font-size:10.5px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin:12px 0 4px;}
.feed-row{display:flex;justify-content:space-between;font-size:13px;padding:3px 0;color:var(--ink);}
.feed-row__num{color:var(--muted);}

.chip{display:inline-block;font-size:10.5px;font-weight:600;letter-spacing:.1em;padding:3px 10px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--muted);}
.chip--up{color:var(--up);border-color:var(--up);}
.chip--signal{color:var(--signal);border-color:var(--signal);}

.warn-line{font-size:12px;color:var(--signal);padding:3px 0;line-height:1.5;}
.gap-line{font-size:12px;color:var(--muted);margin:-2px 0 8px;}

.msg-user code{font-size:13px;color:var(--ink);background:var(--card2);border:1px solid var(--border);padding:6px 10px;border-radius:10px;display:inline-block;white-space:pre-wrap;}
.bot-rule{height:2px;width:40px;background:var(--accent);border-radius:2px;margin:14px 0 4px;}

[data-testid="stVerticalBlockBorderWrapper"]{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:14px!important;}
button[kind="primary"]{border-radius:8px !important;font-weight:600 !important;background:var(--btn-bg) !important;border-color:var(--btn-bg) !important;color:var(--btn-fg) !important;}
button[kind="primary"]:hover{opacity:.85;}
[data-testid="stSidebar"]{background:var(--canvas);border-right:none;}
[data-testid="stExpander"], [data-testid="stExpanderDetails"]{background:var(--card);border-color:var(--border);border-radius:12px;}
.stChatInput textarea{background:var(--card2)!important;border:1px solid var(--border)!important;border-radius:10px!important;color:var(--ink)!important;}
hr{border-color:var(--border)!important;}
[data-testid="stSegmentedControl"] *{font-family:'Inter',sans-serif;}
"""
