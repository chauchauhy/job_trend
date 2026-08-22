import html

import streamlit as st

REGION_COLORS: dict[str, str] = {
    "Hong Kong": "#C43A2F",
    "USA": "#27496D",
    "Global": "#3E6B4F",
}

CATEGORY_COLORS: dict[str, str] = {
    "languages": "#27496D",
    "frameworks_web": "#C2401C",
    "cloud_devops": "#0E7C5B",
    "data_ai": "#6B4FA1",
    "databases": "#8A6D1D",
    "mobile": "#B03A5B",
    "practices": "#5A6B60",
}


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, "#5A6B60")


def _esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def inject_theme(region: str) -> None:
    region_color = REGION_COLORS.get(region, REGION_COLORS["Global"])
    css = _CSS.replace("__REGION__", region_color)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_masthead(region: str) -> None:
    region_color = REGION_COLORS.get(region, REGION_COLORS["Global"])
    st.markdown(
        f"""
        <div class="mast">
            <span class="wordmark">JOB<span class="slash">/</span>TREND</span>
            <span class="rtag" style="background:{region_color}">{_esc(region.upper())}</span>
            <span class="mast-note">SKILL DEMAND TAPE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ticker(stats: list, limit: int = 10) -> None:
    cells = "".join(
        f"<span class='cell'><b style='color:{category_color(s.category)}'>{_esc(s.name)}</b>"
        f"<span class='num'>&nbsp;+{s.count}</span><span class='tri' style='color:{category_color(s.category)}'>▲</span></span>"
        for s in stats[:limit]
    )
    st.markdown(
        f"<div class='tape'><div class='tape__track'>{cells}{cells}</div></div>",
        unsafe_allow_html=True,
    )


def skill_bars(stats: list, limit: int = 12) -> None:
    top = stats[:limit]
    max_count = top[0].count if top else 1
    rows = "".join(
        f"""
        <div class="row">
            <span class="row__name">{_esc(s.name)}</span>
            <span class="row__track"><span class="row__fill" style="width:{round(s.count / max_count * 100, 1)}%;background:{category_color(s.category)}"></span></span>
            <span class="row__num">{s.count} · {s.pct}%</span>
        </div>
        """
        for s in top
    )
    st.markdown(f"<div class='bars'>{rows}</div>", unsafe_allow_html=True)


def dash_head(title: str, count_label: str) -> None:
    st.markdown(
        f"""
        <div class="dash-head">
            <span class="dash-title">{_esc(title)}</span>
            <span class="dash-count">{_esc(count_label)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def category_mix(stats: list) -> None:
    totals: dict[str, int] = {}
    for s in stats:
        totals[s.category] = totals.get(s.category, 0) + s.count
    grand = sum(totals.values()) or 1
    parts = [
        f"<span style='color:{category_color(cat)}'>●</span> {cat} {round(n / grand * 100)}%"
        for cat, n in sorted(totals.items(), key=lambda kv: -kv[1])
    ]
    st.markdown(f"<div class='cat-mix'>MIX&nbsp;&nbsp;{'&nbsp;&nbsp;·&nbsp;&nbsp;'.join(parts)}</div>", unsafe_allow_html=True)


def status_chip(text: str, tone: str = "neutral") -> None:
    tone_class = {"up": "chip--up", "signal": "chip--signal", "neutral": "chip--neutral"}.get(tone, "chip--neutral")
    st.markdown(f"<span class='chip {tone_class}'>{_esc(text)}</span>", unsafe_allow_html=True)


def side_label(label: str) -> None:
    st.markdown(f"<div class='side-label'>{_esc(label)}</div>", unsafe_allow_html=True)


def feed_row(left: str, right: str) -> None:
    st.markdown(
        f"<div class='feed-row'><span>{_esc(left)}</span><span class='feed-row__num'>{_esc(right)}</span></div>",
        unsafe_allow_html=True,
    )


def warn_line(text: str) -> None:
    st.markdown(f"<div class='warn-line'>⌁ {_esc(text)}</div>", unsafe_allow_html=True)


def bot_rule() -> None:
    st.markdown("<div class='bot-rule'></div>", unsafe_allow_html=True)


def user_line(text: str) -> None:
    st.markdown(f"<div class='msg-user'><code>&gt; {_esc(text)}</code></div>", unsafe_allow_html=True)


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Instrument+Sans:wght@400;500;600&family=Spline+Sans+Mono:wght@400;500;600&display=swap');

:root{
    --desk:#ECEFEA; --panel:#E3E8DF; --ink:#161D1A; --muted:#5A6B60;
    --line:#C8CEC6; --up:#0E7C5B; --signal:#C2401C;
    --region:__REGION__;
}
.stApp{background:var(--desk);color:var(--ink);font-family:'Instrument Sans',system-ui,sans-serif;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:1.2rem;}

.mast{display:flex;align-items:center;gap:14px;padding:2px 2px 8px;border-bottom:3px solid var(--region);}
.wordmark{font-family:'Archivo Black',sans-serif;font-size:27px;line-height:1;text-transform:uppercase;letter-spacing:.5px;color:var(--ink);}
.wordmark .slash{color:var(--up);}
.rtag{font-family:'Spline Sans Mono',monospace;font-size:11.5px;font-weight:600;color:#fff;padding:4px 12px;border-radius:999px;letter-spacing:.12em;}
.mast-note{margin-left:auto;font-family:'Spline Sans Mono',monospace;font-size:11px;letter-spacing:.18em;color:var(--muted);}

.tape{overflow:hidden;background:var(--panel);border-bottom:1px solid var(--line);padding:7px 0;margin-bottom:10px;}
.tape__track{display:inline-flex;white-space:nowrap;width:max-content;animation:tape 38s linear infinite;}
.tape:hover .tape__track{animation-play-state:paused;}
.cell{font-family:'Spline Sans Mono',monospace;font-size:13px;padding:0 20px;border-right:1px solid var(--line);}
.cell .num{color:var(--ink);}
.cell .tri{font-size:10px;margin-left:5px;}
@keyframes tape{to{transform:translateX(-50%);}}
@media (prefers-reduced-motion: reduce){.tape__track{animation:none;}}

.dash-head{display:flex;justify-content:space-between;align-items:baseline;margin:16px 0 6px;}
.dash-title{font-family:'Archivo Black',sans-serif;font-size:19px;text-transform:uppercase;letter-spacing:.03em;}
.dash-count{font-family:'Spline Sans Mono',monospace;font-size:12px;letter-spacing:.14em;color:var(--muted);}

.bars .row{display:flex;align-items:center;gap:12px;padding:7px 0;border-bottom:1px solid var(--line);}
.row:last-child{border-bottom:none;}
.row__name{flex:0 0 180px;font-weight:600;font-size:14.5px;}
.row__track{flex:1;height:13px;background:var(--panel);}
.row__fill{display:block;height:100%;border-radius:0 2px 2px 0;}
.row__num{flex:0 0 92px;text-align:right;font-family:'Spline Sans Mono',monospace;font-size:12.5px;color:var(--muted);}

.cat-mix{font-family:'Spline Sans Mono',monospace;font-size:12px;color:var(--muted);margin-top:12px;}

.side-label{font-family:'Spline Sans Mono',monospace;font-size:10.5px;letter-spacing:.16em;color:var(--muted);text-transform:uppercase;margin:12px 0 4px;}
.feed-row{display:flex;justify-content:space-between;font-family:'Spline Sans Mono',monospace;font-size:13px;padding:2px 0;}
.feed-row__num{color:var(--muted);}

.chip{display:inline-block;font-family:'Spline Sans Mono',monospace;font-size:11px;font-weight:600;letter-spacing:.12em;padding:3px 11px;border-radius:999px;border:1.5px solid var(--line);}
.chip--up{color:var(--up);border-color:var(--up);}
.chip--signal{color:var(--signal);border-color:var(--signal);}
.chip--neutral{color:var(--muted);}

.warn-line{font-family:'Spline Sans Mono',monospace;font-size:11.5px;color:var(--signal);padding:3px 0;line-height:1.45;}

.msg-user code{font-family:'Spline Sans Mono',monospace;font-size:13.5px;color:var(--ink);background:var(--panel);padding:6px 10px;border-radius:6px;display:inline-block;white-space:pre-wrap;}
.bot-rule{height:3px;width:52px;background:var(--region);margin:16px 0 4px;}

.stChatInput textarea, div[data-testid="stChatInput"] textarea{background:#fff;}
button[kind="primary"]{border-radius:6px !important;font-family:'Instrument Sans',sans-serif !important;}
[data-testid="stSidebar"]{background:var(--desk);border-right:1px solid var(--line);}
[data-testid="stExpander"]{border-color:var(--line);}
.stDataFrame{font-family:'Spline Sans Mono',monospace;}
"""
