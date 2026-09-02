import re

from config import settings
from src.models import Job
from src.sources.base import get_json, strip_html, usa_region

_NUM_TOKEN = r"(?:([€£$]))?\s*([\d][\d\.,]*)\s*([k])?"
_AMOUNT_RE = re.compile(_NUM_TOKEN + r"\b", re.IGNORECASE)
_CURRENCY_SYMBOL = {"$": "USD", "€": "EUR", "£": "GBP"}
_PERIOD_HOURLY_RE = re.compile(r"/\s*h(?:r|our)?\b|\bper\s*hour\b|hourly", re.IGNORECASE)
_PERIOD_MONTHLY_RE = re.compile(r"/\s*mo(?:nth)?\b|\bper\s*month\b|monthly", re.IGNORECASE)
_PERIOD_YEARLY_RE = re.compile(r"/\s*y\b|\bper\s*year\b|annual", re.IGNORECASE)


def fetch() -> tuple[list[Job], str | None]:
    data, error = get_json(
        settings.api.remotive_url,
        params={"category": "software-dev"},
    )
    if error:
        return [], error
    items = data.get("jobs", []) if isinstance(data, dict) else []
    return [_to_job(item) for item in items if item.get("title")], None


def _amount(match: "re.Match[str]") -> int:
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


def _parse_salary(raw) -> tuple[int | None, int | None, str | None, str | None]:
    if not raw or not str(raw).strip():
        return None, None, None, None
    text = str(raw)
    matches = list(_AMOUNT_RE.finditer(text))
    amounts = [_amount(m) for m in matches]
    if not amounts:
        return None, None, None, None
    low, high = amounts[0], amounts[-1]
    if low > high:
        low, high = high, low
    symbol = next((m.group(1) for m in matches if m.group(1)), None)
    if not symbol:
        symbol = next((s for s in _CURRENCY_SYMBOL if s in text), None)
    currency = _CURRENCY_SYMBOL.get(symbol) if symbol else None
    if _PERIOD_HOURLY_RE.search(text):
        period = "HOURLY"
    elif _PERIOD_MONTHLY_RE.search(text):
        period = "MONTHLY"
    elif _PERIOD_YEARLY_RE.search(text):
        period = "YEARLY"
    else:
        period = "YEARLY"
    return low, high, currency, period


def _to_job(item: dict) -> Job:
    location = str(item.get("candidate_required_location") or "")
    tags = tuple(t.strip() for t in (item.get("tags") or []) if t and t.strip())
    salary_min, salary_max, salary_currency, salary_period = _parse_salary(item.get("salary"))
    return Job(
        id=f"remotive:{item.get('id')}",
        source="remotive",
        title=str(item["title"]),
        company=item.get("company_name") or "",
        location=location,
        regions=frozenset({usa_region(location)}),
        description=strip_html(item.get("description")),
        url=item.get("url") or "",
        published_at=item.get("publication_date"),
        tags=tags,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        salary_period=salary_period,
    )
