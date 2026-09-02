import re
import statistics
from dataclasses import dataclass
from typing import Iterable

from config import FX_RATES
from src.models import Job

_SENIORITY = (
    "senior/principal",
    "principal",
    "senior staff",
    "staff senior",
    "senior",
    "lead",
    "staff",
    "junior",
    "mid-level",
    "mid level",
    "mid",
    "entry-level",
    "entry level",
    "intern",
    "sr.",
    "sr",
    "jr.",
    "jr",
)

_PAREN_RE = re.compile(r"\s*\([^)]*\)")
_SUFFIX_RE = re.compile(r"\s+[-–—]\s+.*$")

_CURRENCY_SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£"}
_SYMBOL_CURRENCY = {"€": "EUR", "£": "GBP"}

_SALARY_NUMBER_RE = re.compile(r"(?:([€£$]))?\s*([\d][\d\.,]*)([kK])?")
_BAD_SCALE_RE = re.compile(r"(?i)\s*(?:million|billion|trillion|[mb]\b)")
_SALARY_KEYWORD_RE = re.compile(
    r"salary|compensation|\bpay\b|\bper\s*hour\b|\bper\s*year\b|\bper\s*month\b|"
    r"monthly|hourly|annual|wage|\brange\b|\brate\b",
    re.IGNORECASE,
)
_RANGE_SEP_RE = re.compile(r"(?:-|–|—|to|\.\.\.?)", re.IGNORECASE)
_SYMBOL_OR_CURRENCY_RE = re.compile(r"[$€£]|\b(?:hkd|usd|eur|gbp|cny)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class SalaryValue:
    min_value: int | None
    max_value: int | None
    currency: str | None
    period: str | None
    source: str


@dataclass(frozen=True, slots=True)
class SalaryRow:
    title: str
    jobs: int
    with_salary: int
    salary_min: int | None
    salary_max: int | None
    median: int | None
    currency: str
    period: str
    median_annual: int | None = None
    source: str = ""


@dataclass(frozen=True, slots=True)
class RegionSalary:
    with_salary: int
    median: int | None
    salary_min: int | None
    salary_max: int | None
    currency: str | None
    period: str | None


def normalize_title(title: str) -> str:
    text = title.strip()
    text = _PAREN_RE.sub("", text)
    text = _SUFFIX_RE.sub("", text).strip()
    lowered = text.lower()
    for word in _SENIORITY:
        prefix = word + " "
        if lowered.startswith(prefix):
            text = text[len(prefix) :]
            lowered = text.lower()
    text = " ".join(text.split()).strip()
    return text or title.strip()


def has_salary(job: Job) -> bool:
    return job.salary_min is not None or job.salary_max is not None


def midpoint(job: Job) -> int | None:
    low, high = job.salary_min, job.salary_max
    if low is None and high is None:
        return None
    if low is None:
        return high
    if high is None:
        return low
    return (low + high) // 2


def _single(list_: Iterable[str]) -> str:
    values = list(list_)
    unique = {v for v in values if v}
    if len(unique) == 1:
        return next(iter(unique))
    return "mixed" if unique else ""


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
    if re.search(r"/\s*mo(?:nth)?\b|\bper\s*month\b|monthly|月薪|每月", text, re.IGNORECASE):
        return "MONTHLY"
    return "YEARLY"


def _find_amounts(text: str) -> list[re.Match[str]]:
    found: list[re.Match[str]] = []
    for match in _SALARY_NUMBER_RE.finditer(text):
        tail = text[match.end() : match.end() + 12]
        if _BAD_SCALE_RE.match(tail):
            continue
        found.append(match)
        if len(found) >= 3:
            break
    return found


def _currency_of_text(symbol: str | None, default_currency: str | None) -> str | None:
    if symbol == "$":
        return default_currency or "USD"
    if symbol is not None:
        return _SYMBOL_CURRENCY.get(symbol)
    return default_currency


def parse_salary_text(text: str | None, default_currency: str | None = None) -> SalaryValue | None:
    if not text:
        return None
    text = text if isinstance(text, str) else str(text)
    matches = _find_amounts(text)
    if not matches:
        return None
    symbol = next((m.group(1) for m in matches if m.group(1)), None)
    currency = _currency_of_text(symbol, default_currency)

    window_left = text[max(0, matches[0].start() - 40) : matches[0].end()]
    window_right = text[matches[0].start() : matches[0].end() + 15]
    near_keyword = bool(_SALARY_KEYWORD_RE.search(window_left) or _SALARY_KEYWORD_RE.search(window_right))

    if len(matches) >= 2:
        gap = text[matches[0].end() : matches[1].start()]
        if _RANGE_SEP_RE.search(gap) and gap.strip():
            window_start = max(0, matches[0].start() - 40)
            window_end = min(len(text), matches[1].end() + 15)
            window = text[window_start:window_end]
            anchored = bool(_SYMBOL_OR_CURRENCY_RE.search(window)) or bool(_SALARY_KEYWORD_RE.search(window))
            if anchored:
                low, high = _to_amount(matches[0]), _to_amount(matches[1])
                if low > high:
                    low, high = high, low
                return SalaryValue(low, high, currency, _period_of(text), "description")

    amount = _to_amount(matches[0])
    if not near_keyword:
        return None
    return SalaryValue(amount, amount, currency, _period_of(text), "description")


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


def job_salary(job: Job, default_currency: str | None = None) -> SalaryValue | None:
    if job.salary_min is not None or job.salary_max is not None:
        return SalaryValue(
            job.salary_min,
            job.salary_max,
            job.salary_currency or default_currency,
            job.salary_period,
            "api",
        )
    return parse_salary_text(job.description, default_currency)


def _plausible_annual(job: Job, default_currency: str | None) -> dict | None:
    value = job_salary(job, default_currency)
    if value is None:
        return None
    low = annualize(value.min_value, value.period) if value.min_value is not None else None
    high = annualize(value.max_value, value.period) if value.max_value is not None else None
    if low is None and high is None:
        return None
    mid = (low + high) // 2 if low is not None and high is not None else (low if low is not None else high)
    if not _is_plausible(mid, value.currency):
        return None
    raw_mid = (
        (value.min_value + value.max_value) // 2
        if value.min_value is not None and value.max_value is not None
        else (value.min_value if value.min_value is not None else value.max_value)
    )
    return {
        "value": value,
        "low": low,
        "high": high,
        "mid": mid,
        "raw_mid": raw_mid,
    }


def salary_breakdown(jobs: list[Job], default_currency: str | None = None) -> list[SalaryRow]:
    groups: dict[str, list[Job]] = {}
    for job in jobs:
        groups.setdefault(normalize_title(job.title), []).append(job)

    rows: list[SalaryRow] = []
    for title, group in groups.items():
        paid = [x for x in (_plausible_annual(j, default_currency) for j in group) if x]
        rows.append(
            SalaryRow(
                title=title,
                jobs=len(group),
                with_salary=len(paid),
                salary_min=min((x["value"].min_value for x in paid), default=None),
                salary_max=max((x["value"].max_value for x in paid), default=None),
                median=int(statistics.median([x["raw_mid"] for x in paid])) if paid else None,
                currency=_single(x["value"].currency for x in paid),
                period=_single(x["value"].period for x in paid),
                median_annual=int(statistics.median([x["mid"] for x in paid])) if paid else None,
                source=_single(x["value"].source for x in paid),
            )
        )
    rows.sort(key=lambda r: (-r.with_salary, -r.jobs, r.title.lower()))
    return rows


def region_salary(jobs: list[Job], default_currency: str | None = None) -> RegionSalary:
    paid = [x for x in (_plausible_annual(j, default_currency) for j in jobs) if x]
    if not paid:
        return RegionSalary(0, None, None, None, None, None)
    currency_counts: dict[str, int] = {}
    for x in paid:
        cur = x["value"].currency
        if cur:
            currency_counts[cur] = currency_counts.get(cur, 0) + 1
    currency = max(currency_counts, key=currency_counts.get) if currency_counts else None
    currency_pool = [x for x in paid if currency is None or x["value"].currency == currency]

    period_counts: dict[str, int] = {}
    for x in currency_pool:
        period = x["value"].period
        if period:
            period_counts[period] = period_counts.get(period, 0) + 1
    period = _dominant_period(period_counts)
    pool = [x for x in currency_pool if period is None or x["value"].period == period]

    medians = [x["mid"] for x in pool if x["mid"] is not None]
    return RegionSalary(
        with_salary=len(pool),
        median=int(statistics.median(medians)) if medians else None,
        salary_min=min((x["low"] for x in pool), default=None),
        salary_max=max((x["high"] for x in pool), default=None),
        currency=currency,
        period=period,
    )


def _dominant_period(counts: dict[str, int]) -> str | None:
    if not counts:
        return None
    top = max(counts, key=lambda p: (counts[p], p == "YEARLY"))
    return top if counts[top] > 1 else None


def seniority_of(title: str) -> str:
    text = title.lower()
    if re.search(r"principal", text):
        return "principal"
    if re.search(r"senior|sr\.?", text):
        return "senior"
    if re.search(r"staff", text):
        return "staff"
    if re.search(r"\blead\b", text):
        return "lead"
    if re.search(r"junior|jr\.?", text):
        return "junior"
    return "other"


def seniority_breakdown(jobs: list[Job], default_currency: str | None = None) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for job in jobs:
        level = seniority_of(job.title)
        groups.setdefault(level, []).append(_plausible_annual(job, default_currency))
    order = ["principal", "senior", "staff", "lead", "junior", "other"]
    rows: list[dict] = []
    for level in order:
        if level not in groups:
            continue
        paid = [x for x in groups[level] if x]
        rows.append(
            {
                "level": level,
                "jobs": len(groups[level]),
                "with_salary": len(paid),
                "median": int(statistics.median([x["mid"] for x in paid])) if paid else None,
            }
        )
    return rows


def _matched_jobs(jobs: list[Job], matcher) -> dict[str, list[Job]]:
    matched: dict[str, list[Job]] = {name: [] for name in matcher.patterns}
    for job in jobs:
        full_text = " ".join((job.title, job.description, *job.tags))
        for name in matcher.find_in_text(full_text):
            matched[name].append(job)
    return matched


def skill_salary(
    jobs: list[Job],
    matcher,
    default_currency: str | None = None,
    top_n: int = 10,
) -> list[dict]:
    matched = _matched_jobs(jobs, matcher)
    rows: list[dict] = []
    for name, group in matched.items():
        if not group:
            continue
        paid = [x for x in (_plausible_annual(j, default_currency) for j in group) if x]
        rows.append(
            {
                "skill": name,
                "jobs": len(group),
                "with_salary": len(paid),
                "median": int(statistics.median([x["mid"] for x in paid])) if paid else None,
            }
        )
    rows.sort(key=lambda r: (-r["jobs"], -len(str(r["median"] or 0)), r["skill"]))
    return rows[:top_n]


def source_salary(jobs: list[Job], default_currency: str | None = None) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for job in jobs:
        groups.setdefault(job.source, []).append(_plausible_annual(job, default_currency))
    rows: list[dict] = []
    for source, vals in groups.items():
        paid = [x for x in vals if x]
        rows.append(
            {
                "source": source,
                "jobs": len(vals),
                "with_salary": len(paid),
                "median": int(statistics.median([x["mid"] for x in paid])) if paid else None,
            }
        )
    rows.sort(key=lambda r: (-r["jobs"], r["source"]))
    return rows


def money(n: int | None, currency: str | None = None) -> str:
    if n is None:
        return "—"
    symbol = _CURRENCY_SYMBOL.get(currency or "") or (f"{currency} " if currency else "")
    return f"{symbol}{n:,}"


def range_text(row: SalaryRow) -> str:
    if row.salary_min is None and row.salary_max is None:
        return "—"
    cur = row.currency if row.currency not in ("mixed", "") else None
    if row.salary_min is not None and row.salary_max is not None and row.salary_min != row.salary_max:
        return f"{money(row.salary_min, cur)}–{money(row.salary_max, cur)}"
    value = row.salary_min if row.salary_min is not None else row.salary_max
    return money(value, cur)


def median_text(row: SalaryRow) -> str:
    cur = row.currency if row.currency not in ("mixed", "") else None
    return money(row.median, cur)