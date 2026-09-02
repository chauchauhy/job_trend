import time

from config import JSEARCH_COUNTRY, JSEARCH_QUERY_SUFFIX, settings
from src.models import Job
from src.sources.base import get_json, salary_int, strip_html

JSEARCH_DEFAULT_CURRENCY = {
    "USA": "USD",
    "Hong Kong": "HKD",
}

JSEARCH_SALARY_PERIODS = {
    "YEARLY": "YEARLY",
    "YEAR": "YEARLY",
    "ANNUAL": "YEARLY",
    "MONTHLY": "MONTHLY",
    "MONTH": "MONTHLY",
    "HOURLY": "HOURLY",
    "HOUR": "HOURLY",
    "PER_HOUR": "HOURLY",
    "DAILY": "DAILY",
    "DAY": "DAILY",
    "WEEKLY": "WEEKLY",
}


def fetch(keywords: list[str], region: str) -> tuple[list[Job], str | None]:
    api_key = settings.api.jsearch_api_key
    if not api_key:
        return [], None
    jobs: dict[str, Job] = {}
    errors: dict[str, int] = {}
    for keyword in keywords:
        for page in range(1, settings.fetch.jsearch_max_pages_per_keyword + 1):
            data, error = _search_throttled(api_key, keyword, region, page)
            if error:
                errors[error] = errors.get(error, 0) + 1
                break
            items = data.get("data", []) if isinstance(data, dict) else []
            if not items:
                break
            for item in items:
                job = _to_job(item, region)
                if job.title:
                    jobs.setdefault(job.id, job)
            time.sleep(settings.fetch.jsearch_delay_s)
    error_summary = ", ".join(f"{msg} x{count}" for msg, count in sorted(errors.items()))
    return list(jobs.values()), error_summary or None


def _search_throttled(
    api_key: str, keyword: str, region: str, page: int
) -> tuple[dict | None, str | None]:
    data, error = _search(api_key, keyword, region, page)
    if error == "HTTP 429":
        time.sleep(settings.fetch.retry_backoff_s)
        return _search(api_key, keyword, region, page)
    return data, error


def _build_query(keyword: str, region: str) -> str:
    return keyword + JSEARCH_QUERY_SUFFIX.get(region, "")


def _search(api_key: str, keyword: str, region: str, page: int) -> tuple[dict | None, str | None]:
    params: dict[str, object] = {
        "query": _build_query(keyword, region),
        "page": page,
        "num_pages": 1,
        "date_posted": "all",
    }
    country = JSEARCH_COUNTRY.get(region)
    if country:
        params["country"] = country
    return get_json(
        f"{settings.api.jsearch_base_url}/search",
        params=params,
        headers={"x-api-key": api_key},
    )


def _to_job(item: dict, region: str) -> Job:
    location_parts = [item[k] for k in ("job_city", "job_state", "job_country") if item.get(k)]
    raw_skills = item.get("job_required_skills")
    if isinstance(raw_skills, str):
        tags = tuple(t.strip() for t in raw_skills.split(",") if t.strip())
    else:
        tags = tuple(str(t).strip() for t in (raw_skills or []) if t)
    currency = item.get("job_salary_currency") or None
    if currency is None and (item.get("job_min_salary") is not None or item.get("job_max_salary") is not None):
        currency = JSEARCH_DEFAULT_CURRENCY.get(region)
    period = JSEARCH_SALARY_PERIODS.get(item.get("job_salary_period")) if item.get("job_salary_period") else None
    return Job(
        id=f"jsearch:{item.get('job_id', '')}",
        source="jsearch",
        title=item.get("job_title") or "",
        company=item.get("employer_name") or "",
        location=" · ".join(location_parts),
        regions=frozenset({region}),
        description=strip_html(item.get("job_description")),
        url=item.get("job_apply_link") or "",
        published_at=item.get("job_posted_at_datetime_utc"),
        tags=tags[:15],
        salary_min=salary_int(item.get("job_min_salary")),
        salary_max=salary_int(item.get("job_max_salary")),
        salary_currency=currency,
        salary_period=period,
    )
