# Salary Analytics Block v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (``- [ ]``) syntax for tracking.

**Goal:** Upgrade the salary block into a unified analytics section: description-salary coverage, annual standardization, cross-region comparison, seniority/skill/source breakdowns, salary trend over pulls, and chat intents.

**Architecture:** Salary derivation moves to analysis time (`src/analysis/salary.py`): prefer structured API fields, fall back to a noise-controlled description parser; all aggregation uses annualized midpoints, filtered by a plausibility cap, grouped by dominant currency+period cohort. History snapshots gain a `salary` payload. A new UI section plus chat intents surface the stats.

**Tech Stack:** Python 3, Streamlit, pandas, Altair, pytest.

**Spec:** design agreed in-session (grilling rounds 1–2). Not an external file.

## Global Constraints

- No new dependencies; only Streamlit/pandas/Altair/pytest already used.
- Cache schema stays v2 (`CACHE_SCHEMA_VERSION == 2`); no re-pull needed — descriptions already cached.
- Salary parsing must NOT treat funding figure noise (`$475M`, `$11M`, `$85+ million`, `$9 trillion`) as salaries.
- Sanity cap: annualized USD-equivalent must be in `[5000, 1_000_000]` to enter aggregate stats.
- All user-visible copy in the UI remains English (existing app language).

---

### Task 1: FX rates in config.py

**Files:**
- Modify: `config.py` (after `REGION_ALIASES`, before `Settings`)

**Interfaces:**
- Produces: module constant `FX_RATES: dict[str, float]` = units per 1 USD (e.g. `{"HKD": 7.8, "EUR": 0.92, "GBP": 0.79, "CAD": 1.36, "AUD": 1.52}`).

- [ ] **Step 1: Add constant**

```python
FX_RATES: dict[str, float] = {
    "HKD": 7.80,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.36,
    "AUD": 1.52,
}
```

- [ ] **Step 2: Verify import**

Run: `.venv/bin/python -c "from config import FX_RATES; print(FX_RATES['HKD'])"`
Expected: `7.8`

- [ ] **Step 3: Commit**

```bash
git add config.py && git commit -m "feat: add static FX_RATES for salary USD comparison"
```

---

### Task 2: salary parser + annualize + plausibility + job_salary (src/analysis/salary.py)

**Files:**
- Modify: `src/analysis/salary.py`
- Test: `tests/test_salary.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True, slots=True) SalaryValue: min_value: int | None; max_value: int | None; currency: str | None; period: str | None; source: str`  (`source` in `{"api","description"}`)
  - `parse_salary_text(text: str, default_currency: str | None) -> SalaryValue | None` — handles `$lo–$hi`, `$lo - $hi`, single amounts, `k` suffix, European decimal comma; ignores amounts followed by `million/billion/trillion/M/B`; ignores single amounts >25 chars from a salary keyword.
  - `_SALARY_KEYWORDS = ("salary", "compensation", "pay ", "per hour", "per year", "monthly", "hourly", "annual", "wage", "range", "rate")` (word-ish checks)
  - `annualize(value: int, period: str | None) -> int` — HOURLY×2080, MONTHLY×12, DAILY×260, WEEKLY×52, else ×1.
  - `salary_to_usd(value: int, currency: str | None) -> int` — `value / FX_RATES.get(currency, 1)`.
  - `_is_plausible(value: int, currency: str | None) -> bool` — `5000 <= salary_to_usd(value, currency) <= 1_000_000`.
  - `job_salary(job: Job, default_currency: str | None = None) -> SalaryValue | None`
- Uses: `src.models.Job`, `config.FX_RATES`.

- [ ] **Step 1–2: Write failing tests, run to fail**

Add to `tests/test_salary.py`:

```python
from src.analysis.salary import annualize, job_salary, parse_salary_text, salary_to_usd

def test_annualize_scales_periods():
    assert annualize(100, "HOURLY") == 208_000
    assert annualize(5_000, "MONTHLY") == 60_000
    assert annualize(10_000, "YEARLY") == 10_000
    assert annualize(10_000, None) == 10_000

def test_parse_salary_range_and_k_suffix():
    v = parse_salary_text("Compensation $31,2k- $52k", None)
    assert (v.min_value, v.max_value) == (31_200, 52_000)

def test_parse_salary_per_hour_period():
    v = parse_salary_text("Rate $120 - $170 /hour", None)
    assert v.period == "HOURLY"

def test_parse_salary_uk_symbol():
    v = parse_salary_text("£55,000–£70,000 per year", None)
    assert v.currency == "GBP" and v.period == "YEARLY"

def test_parse_salary_ignores_funding_noise():
    assert parse_salary_text("Company raised $475M from investors", None) is None
    assert parse_salary_text("we paid $11M to builders", None) is None
    assert parse_salary_text("earn $85+ million", None) is None
    assert parse_salary_text("$9 trillion in payment volume", None) is None

def test_parse_salary_single_requires_keyword_proximity():
    v = parse_salary_text("Salary range $140,000.", None)
    assert v is not None and v.min_value == 140_000
    assert parse_salary_text("great place to work have fun $300 stipend", None) is None

def test_parse_salary_default_currency():
    v = parse_salary_text("月薪 $40,000 - $60,000 per month", "HKD")
    assert v.currency == "HKD" and v.period == "MONTHLY"

def test_salary_to_usd():
    assert salary_to_usd(78_000, "HKD") == 10_000
    assert salary_to_usd(120_000, "USD") == 120_000

def test_job_salary_prefers_structured():
    from tests.helpers import make_job
    job = make_job(salary_min=90_000, salary_max=110_000, salary_currency="USD", salary_period="YEARLY")
    v = job_salary(job)
    assert v.source == "api" and v.max_value == 110_000

def test_job_salary_falls_back_to_description():
    from tests.helpers import make_job
    job = make_job(description="The base salary range is $80,000 - $95,000 per year.")
    v = job_salary(job, "USD")
    assert v.source == "description" and v.min_value == 80_000

def test_job_salary_none_without_salary():
    from tests.helpers import make_job
    assert job_salary(make_job(description="No pay disclosed. Apply today!")) is None
```

Run: `.venv/bin/python -m pytest tests/test_salary.py -q`
Expected: FAIL (`ImportError` / no attribute).

- [ ] **Step 3: Implement in `src/analysis/salary.py`**

Append constants + functions (keep existing `_SENIORITY`, `_PAREN_RE`, `_SUFFIX_RE`, `_CURRENCY_SYMBOL`):

```python
import re
from config import FX_RATES
from src.models import Job

_SALARY_KEYWORD_RE = re.compile(
    r"salary|compensation|\bpay\b|\bper\s*hour\b|\bper\s*year\b|\bper\s*month\b|monthly|hourly|annual|wage|\brange\b|\brate\b",
    re.IGNORECASE,
)
_SALARY_NUMBER_RE = re.compile(r"(?:([€£$]))?\s*([\d][\d\.,]*)([kK])?")
_BAD_SCALE_RE = re.compile(r"(?i)\s*(?:million|billion|trillion|[mbt]\b)")

@dataclass(frozen=True, slots=True)
class SalaryValue:
    min_value: int | None
    max_value: int | None
    currency: str | None
    period: str | None
    source: str


def _to_amount(match: re.Match[str]) -> int:
    raw = match.group(2).replace("\u00a0", "").strip()
    if "," in raw:
        parts = raw.split(",")
        if 1 <= len(parts[-1]) <= 2:
            raw = raw.replace(",", ".")
        else:
            raw = raw.replace(",", "")
    value = float(raw)
    if match.group(3):
        value *= 1000
    return int(value)


def _period_of(text: str) -> str | None:
    if re.search(r"/\s*h(?:r|our)?\b|\bper\s*hour\b|hourly", text, re.IGNORECASE):
        return "HOURLY"
    if re.search(r"/\s*mo(?:nth)?\b|\bper\s*month\b|monthly", text, re.IGNORECASE):
        return "MONTHLY"
    if re.search(r"/\s*y\b|\bper\s*year\b|annual", text, re.IGNORECASE):
        return "YEARLY"
    return "YEARLY"


def _find_amounts(text: str) -> list[re.Match[str]]:
    return [m for m in _SALARY_NUMBER_RE.finditer(text) if not _BAD_SCALE_RE.match(text[m.end() : m.end() + 12])]


def parse_salary_text(text: str, default_currency: str | None) -> SalaryValue | None:
    if not text:
        return None
    text = text if isinstance(text, str) else str(text)
    matches = _find_amounts(text)[:3]
    if not matches:
        return None
    symbol = next((m.group(1) for m in matches if m.group(1)), None)
    currency = _CURRENCY_SYMBOL.get(symbol) if symbol else default_currency

    # range: two amounts separated by - / – / — / to
    if len(matches) >= 2:
        gap = text[matches[0].end() : matches[1].start()]
        if re.search(r"\s*(?:-|–|—|to|\.\.\.?)\s*$", gap) or re.search(r"(?:[-\u2013\u2014]|to)", gap):
            low, high = _to_amount(matches[0]), _to_amount(matches[1])
            if low > high:
                low, high = high, low
            return SalaryValue(low, high, currency, _period_of(text), "description")

    low = high = _to_amount(matches[0])
    # single value only when near a salary keyword
    window_left = text[max(0, matches[0].start() - 40) : matches[0].end()]
    if not _SALARY_KEYWORD_RE.search(window_left) and not _SALARY_KEYWORD_RE.search(text[matches[0].start() : matches[0].start() + 15]):
        return None
    return SalaryValue(low, high, currency, _period_of(text), "description")


def _currency_of(job: Job) -> str | None:
    return job.salary_currency or None


def job_salary(job: Job, default_currency: str | None = None) -> SalaryValue | None:
    if job.salary_min is not None or job.salary_max is not None:
        currency = job.salary_currency or default_currency
        return SalaryValue(job.salary_min, job.salary_max, currency, job.salary_period, "api")
    parsed = parse_salary_text(job.description, default_currency)
    return parsed


def annualize(value: int, period: str | None) -> int:
    if period == "HOURLY":
        return value * 2080
    if period == "MONTHLY":
        return value * 12
    if period == "DAILY":
        return value * 260
    if period == "WEEKLY":
        return value * 52
    return value


def salary_to_usd(value: int, currency: str | None) -> int:
    return int(value / FX_RATES.get(currency or "", 1))


def _is_plausible(annual: int, currency: str | None) -> bool:
    return 5_000 <= salary_to_usd(annual, currency) <= 1_000_000
```

Add `FX_RATES` import at top: `from config import FX_RATES`.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_salary.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/analysis/salary.py tests/test_salary.py && git commit -m "feat: salary text parser + annualize + plausibility (salary.py)"
```

---

### Task 3: aggregations rewrite (breakdown/region/seniority/skill/source)

**Files:**
- Modify: `src/analysis/salary.py`
- Test: `tests/test_salary.py`

**Interfaces:**
- Produces:
  - `SalaryRow` extended: add `median_annual: int | None`, `source: str`.
  - `region_salary(jobs, default_currency: str | None = None) -> RegionSalary` — now uses `job_salary`, plausible filter, dominant currency→dominant period cohort; `median` is the **annualized** median.
  - `seniority_of(title: str) -> str` — one of `senior|staff|lead|principal|junior|other`.
  - `seniority_breakdown(jobs) -> list[dict]` — `{"level","jobs","with_salary","median"}`.
  - `skill_salary(jobs, matcher, default_currency=None, top_n=10) -> list[dict]` — `{"skill","jobs","with_salary","median"}` sorted by `jobs` desc.
  - `source_salary(jobs, default_currency=None) -> list[dict]` — `{"source","jobs","with_salary","median"}`.
- Consumes: Task 2 functions.

- [ ] **Step 1–2: failing tests**

```python
def test_salary_breakdown_uses_description_and_annualizes():
    jobs = [
        make_job(job_id="1", title="Backend Engineer", description="Salary $100,000 - $140,000 per year"),
        make_job(job_id="2", title="Backend Engineer", description="Compensation $120,000 - $160,000 per year"),
        make_job(job_id="3", title="Backend Engineer", description="no pay"),
        make_job(job_id="4", title="Frontend Engineer", description="RATE $50 per hour"),
    ]
    rows = salary_breakdown(jobs, default_currency="USD")
    backend = next(r for r in rows if r.title == "Backend Engineer")
    assert backend.with_salary == 2 and backend.median_annual == 130_000
    front = next(r for r in rows if r.title == "Frontend Engineer")
    assert front.median_annual == 104_000

def test_salary_breakdown_drops_implausible():
    jobs = [make_job(job_id="1", title="Eng", description="Salary range $2,000,000 - $3,000,000 per year")]
    assert salary_breakdown(jobs, default_currency="USD") == []

def test_region_salary_annualizes_and_filters_period():
    jobs = [
        make_job(job_id="1", title="Eng A", description="Rate $100 - $200 /hour"),
        make_job(job_id="2", title="Eng B", description="Rate $120 - $170 /hour"),
        make_job(job_id="3", title="Eng C", description="Salary $100,000 - $120,000 per year"),
    ]
    summary = region_salary(jobs, default_currency="USD")
    assert summary.period == "HOURLY"
    assert summary.with_salary == 2
    assert summary.median == 147 * 2080 // 1  # (150+145)/2 → 147 avg midpoint? see median def

def test_seniority_detection():
    assert seniority_of("Senior Backend Engineer") == "senior"
    assert seniority_of("Staff Engineer") == "staff"
    assert seniority_of("Lead Engineer") == "lead"
    assert seniority_of("Principal Engineer") == "principal"
    assert seniority_of("Junior Engineer") == "junior"
    assert seniority_of("Backend Engineer") == "other"

def test_skill_salary_returns_top_by_count():
    from src.analysis.skills import SkillMatcher
    jobs = [
        make_job(job_id="1", title="Python Dev", description="python Salary $120,000 - $140,000 per year"),
        make_job(job_id="2", title="Full Stack", description="python Salary $110,000 - $130,000 per year"),
        make_job(job_id="3", title="Go Dev", description="go Salary $150,000 per year"),
    ]
    skill_rows = skill_salary(jobs, SkillMatcher(), default_currency="USD")
    python = next(r for r in skill_rows if r["skill"] == "python")
    assert python["jobs"] == 2 and python["median"] == 125_000

def test_source_salary_grouping():
    jobs = [
        make_job(job_id="1", source="jobicy", description="Salary $90,000 per year"),
        make_job(job_id="2", source="remotive", description="Salary $100,000 per year"),
    ]
    rows = source_salary(jobs, default_currency="USD")
    assert {r["source"] for r in rows} == {"jobicy", "remotive"}
```

Run and confirm fail.

- [ ] **Step 3: Implement**

Rewrite `salary_breakdown`, `region_salary`, extend `SalaryRow`, add helpers. Full replacement of the three aggregations inside `src/analysis/salary.py` (use existing `_single`, `midpoint` helpers).

```python
_SENIORITY_LEVELS = (("principal",), ("senior",), ("staff",), ("lead",), ("junior",))

def _plausible_values(job: Job, default_currency: str | None) -> dict | None:
    v = job_salary(job, default_currency)
    if v is None or (v.min_value is None and v.max_value is None):
        return None
    low = annualize(v.min_value, v.period) if v.min_value is not None else None
    high = annualize(v.max_value, v.period) if v.max_value is not None else None
    midpoint_value = (low + high) // 2 if low is not None and high is not None else (low if low is not None else high)
    if not _is_plausible(midpoint_value, v.currency):
        return None
    return {"value": v, "annual": midpoint_value}
```

`SalaryRow` gains `median_annual: int | None` and `source: str`. `region_salary` uses `job_salary`/plausible + annualized medians. `seniority_of` uses token search. `skill_salary` uses `matcher.find_in_text(" ".join((job.title, job.description, *job.tags)))`.

Note: `make_job` fixture already supports `title/description`.

- [ ] **Step 4: Run**

Run: `.venv/bin/python -m pytest tests/test_salary.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

---

### Task 4: history salary payload + fetch wiring

**Files:**
- Modify: `src/analysis/history.py`, `src/fetch.py`
- Test: `tests/test_history.py`

**Interfaces:**
- `record_snapshot(..., salary: dict | None = None)` — include `"salary": salary` in snapshot dict.
- `pull_and_record(region, *, data_dir=None)` — compute `salary` payload from `region_salary(jobs, default_currency=None)` and pass it.

- [ ] **Step 1: failing tests**

```python
def test_snapshot_with_salary_payload(tmp_path):
    history.record_snapshot("USA", 1000.0, 10, [], data_dir=tmp_path,
        salary={"median_annual": 130000, "with_salary": 4, "total": 10, "currency": "USD", "period": "YEARLY"})
    snaps = history.load_history("USA", data_dir=tmp_path)
    assert snaps[-1]["salary"]["median_annual"] == 130000

def test_old_snapshots_without_salary_load(tmp_path):
    history.record_snapshot("USA", 1000.0, 10, [], data_dir=tmp_path)
    snaps = history.load_history("USA", data_dir=tmp_path)
    assert "salary" not in snaps[-1]
```

- [ ] **Step 2: implement history change**

```python
def record_snapshot(region, ts, total, stats, *, data_dir=None, salary=None):
    snap = {"ts": float(ts), "total": int(total), "skills": {...}}
    if salary is not None:
        snap["salary"] = salary
    ...
```

- [ ] **Step 3: implement fetch wiring**

In `src/fetch.py::pull_and_record`, after computing stats:

```python
from src.analysis.salary import region_salary
...
salary_payload = None
if jobs:
    s = region_salary(jobs)
    if s.with_salary and s.median is not None:
        salary_payload = {"median_annual": s.median, "with_salary": s.with_salary, "total": len(jobs), "currency": s.currency, "period": s.period}
    record_snapshot(region, time.time(), len(jobs), stats, data_dir=data_dir, salary=salary_payload)
```

- [ ] **Step 4: run full history + fetch tests**

Run: `.venv/bin/python -m pytest tests/test_history.py tests/test_fetch.py -q`
Expected: PASS.

- [ ] **Step 5: commit**

---

### Task 5: chat salary intents

**Files:**
- Modify: `src/chat/handler.py`
- Test: `tests/test_handler.py`

**Interfaces:**
- New helper `_salary_context(store, region) -> data` using functions from `src.analysis.salary`.
- New intents (before generic `compare`, after `help`):
  - `salary coverage` / `coverage salary` / `salary.*how many` / `how many.*salary`
  - `highest paying|top pay|highest salary|pos среди highest`
  - `salary by title|salary breakdown`
  - `salary <rl> vs <rl>` / `salary.*compare`
  - generic `salary <skill>` fallback → skill salary table.

- [ ] **Step 1: failing tests**

```python
def test_salary_by_skill_intent(store):
    text, df = respond("salary python", "Hong Kong", store)
    assert "python" in text.lower() and df is not None

def test_salary_highest_paying_intent(store):
    text, df = respond("highest paying titles", "Hong Kong", store)
    assert df is not None and "title" in "".join(df.columns).lower()

def test_salary_by_title_intent(store):
    text, df = respond("salary by title", "Hong Kong", store)
    assert df is not None

def test_salary_coverage_intent(store):
    text, _ = respond("salary coverage", "Hong Kong", store)
    assert "listing" in text.lower() or "salary" in text.lower()

def test_compare_salary_intent(store):
    text, df = respond("compare salary hk vs usa", "Global", store)
    assert df is not None
```

Note: existing `store` fixture jobs have no salary descriptions → expect empty responses handled gracefully (df still returned for title/highest). Update tests accordingly: add salary into the fixture's job descriptions so the checks are meaningful.

- [ ] **Step 2: implement**

Add imports + `_SALARY_*` regex dispatch in `respond()`, and helper functions returning `(text, df)` with `salary_breakdown`, `skill_salary`, `region_salary`, `source_salary`.

Update `_HELP_TEXT` with new examples.

- [ ] **Step 3: run**

Run: `.venv/bin/python -m pytest tests/test_handler.py -q`
Expected: PASS.

- [ ] **Step 4: commit**

---

### Task 6: theme charts (median bar + salary trend)

**Files:**
- Modify: `src/ui/theme.py`

**Interfaces:**
- `salary_from_history(h)` helper reused in app? No — `app` builds frames; theme provides:
  - `salary_median_chart(frame_cols: list[dict]) -> None` — horizontal bar (like `demand_chart`), input list of `{"label","median","tag"}`.
  - `salary_trend_chart(points: list[dict]) -> None` — line chart of `{"ts","median"}`.

- [ ] **Step 1: (small) implement two chart helpers**, keep style tokens (BORDER/MUTED/INK) consistent with existing charts.

```python
def salary_median_chart(rows) -> None:
    import altair as alt
    import pandas as pd
    frame = pd.DataFrame(rows)
    if frame.empty:
        return
    order = frame.sort_values("median")["label"].tolist()
    chart = (alt.Chart(frame)
        .mark_bar(cornerRadius=0, cornerRadiusEnd=3, height=14)
        .encode(
            x=alt.X("median:Q", title=None,
                    axis=alt.Axis(grid=True, gridColor=BORDER, gridDash=[2,4], gridOpacity=0.7,
                                  labelColor=MUTED, tickColor="transparent", domainColor="transparent", labelFontSize=11, format="$,.0f")),
            y=alt.Y("label:N", sort=order, title=None,
                    axis=alt.Axis(labelColor=INK, labelFontSize=13, ticks=False, domain=False, labelFontWeight=600)),
            color=alt.value("#34D399"),
            tooltip=[alt.Tooltip("label:N", title="title"), alt.Tooltip("median:Q", title="median/yr", format="$,.0f")],
        )
        .configure(background="transparent").configure_view(stroke=None)
        .properties(height=24 * len(frame) + 24))
    st.altair_chart(chart, width="stretch")

def salary_trend_chart(points) -> None:
    import altair as alt
    import pandas as pd
    frame = pd.DataFrame(points)
    if frame.empty:
        return
    chart = (alt.Chart(frame).mark_line(point=alt.OverlayMarkDef(size=40), strokeWidth=2)
        .encode(
            x=alt.X("ts:T", title=None, axis=alt.Axis(grid=True, gridColor=BORDER, gridDash=[2,4], gridOpacity=0.7,
                       labelColor=MUTED, tickColor="transparent", domainColor="transparent", labelFontSize=11)),
            y=alt.Y("median:Q", title=None, axis=alt.Axis(grid=True, gridColor=BORDER, gridDash=[2,4], gridOpacity=0.7,
                       labelColor=MUTED, tickColor="transparent", domainColor="transparent", labelFontSize=11, format="$,.0f")),
            color=alt.value("#60A5FA"),
            tooltip=[alt.Tooltip("yearmonthdate(ts):T", title="pulled"), alt.Tooltip("median:Q", title="median/yr", format="$,.0f")],
        )
        .configure(background="transparent").configure_view(stroke=None).properties(height=240))
    st.altair_chart(chart, width="stretch")
```

- [ ] **Step 2: add smoke import test** in `tests/test_app_smoke.py` (charts render when data present) — covered implicitly by existing AppTest with salary-bearing STUB_JOBS.

- [ ] **Step 3: commit**

---

### Task 7: unified salary UI section

**Files:**
- Modify: `src/app.py`

**Interfaces:**
- Consumes: Task 3 aggregation functions, Task 6 charts, `FX_RATES`, `load_history`, `load_cached`.
- Produces: rewritten `_salary_section(jobs)` called from `run()` between `_chart_grid` and `_trend_section`.

- [ ] **Step 1: rewrite `_salary_section`**

Layout:
1. `section_title("Salary analysis", "DISCLOSED ONLY · ANNUALIZED")`
2. Empty jobs → caption; return.
3. Compute `summary = region_salary(jobs, None)`. If `summary.with_salary == 0` → caption "No salary data…"; return.
4. **Cross-region bar (A4):** for each region in `REGIONS`, `load_cached(r)` → `region_salary` → median→USD via `salary_to_usd`; build `{"label": region, "median": usd}` list; render `salary_median_chart`; caption "approx · static FX_RATES".
5. **Summary strip:** `Disclosed on {with_salary}/{len(jobs)} · median {money(median)} · range {money(min)–money(max)} · {currency} {period}`.
6. **Per-title distribution (A1):** top-10 by `with_salary` then `jobs` → `salary_median_chart` rows `{"label": r.title, "median": r.median_annual}`.
7. **Per-title dataframe (A3):** columns `title|jobs|with salary|period|currency|source|range|median (yr)` from `salary_breakdown`.
8. **Expanders:**
   - "Seniority median": `seniority_breakdown` → small dataframe.
   - "Salary by skill": `skill_salary(jobs, get_matcher())` with ⚠️ for skills missing from user stack (`load_own_skills()` / `normalize_skills`), dataframe `skill|jobs|with salary|median (yr)`.
   - "Salary by source": `source_salary(jobs)` → dataframe.
9. **Salary trend (C):** `load_history(region)` → points `{"ts","median"}` from `snap.get("salary", {}).get("median_annual")`; if `< 2` points → caption "builds with each pull…"; else `salary_trend_chart`.

Note: performance — aggregations re-parse descriptions each call; acceptable (≤150 jobs). For readability, compute `rows`, `summary`, `seniority`, `skill`, `source` once at top (each single pass over jobs).

- [ ] **Step 2: run smoke + app tests**

Run: `.venv/bin/python -m pytest tests/test_app_smoke.py -q`
Expected: PASS (STUB_JOBS has salary → section renders).

- [ ] **Step 3: commit**

---

### Task 8: full regression + snapshot refresh

- [ ] **Step 1: run whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 2: live sanity via cached data**

Run:
```bash
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0,'.')
from src.fetch import load_cached
from src.analysis.salary import region_salary, salary_breakdown, skill_salary, source_salary
from src.analysis.skills import get_matcher
for r in ["Hong Kong","USA","Global"]:
    jobs,*_ = load_cached(r)
    print(r, region_salary(jobs, None))
    print("  titles:", [(x.title, x.median_annual) for x in salary_breakdown(jobs)[:3]])
    print("  skills:", skill_salary(jobs, get_matcher())[:3])
PY
```
Expected: HK now yields salary rows from descriptions; plausible values.

- [ ] **Step 3: refresh trend snapshots**

Run: `.venv/bin/python scripts/update_history.py`
Expected: OK all regions; history files now carry `salary`.

- [ ] **Step 4: commit**

```bash
git add -A && git commit -m "feat: unified salary analytics block (parser, aggregations, trend, chat intents)"
```

---

### Verification

- `streamlit run main.py` → switch Market to Hong Kong → salary block shows data (description-derived), cross-region bar, charts, expanders, trend.