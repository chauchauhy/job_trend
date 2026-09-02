from config import settings
from src.models import Job
from src.sources.base import get_json, salary_int, strip_html, usa_region


def fetch() -> tuple[list[Job], str | None]:
    data, error = get_json(
        settings.api.jobicy_url,
        params={"count": settings.fetch.jobicy_count, "industry": "engineering"},
    )
    if error:
        return [], error
    items = data.get("jobs", []) if isinstance(data, dict) else []
    return [_to_job(item) for item in items if item.get("jobTitle")], None


def _to_job(item: dict) -> Job:
    geo = item.get("jobGeo") or ""
    description = " ".join(
        part
        for part in (strip_html(item.get("jobExcerpt")), strip_html(item.get("jobDescription")))
        if part
    )
    tags = tuple(t.strip() for t in (item.get("jobIndustry") or []) if isinstance(t, str) and t.strip())
    salary_min = salary_int(item.get("annualSalaryMin"))
    salary_max = salary_int(item.get("annualSalaryMax"))
    return Job(
        id=f"jobicy:{item.get('id')}",
        source="jobicy",
        title=str(item["jobTitle"]),
        company=item.get("companyName") or "",
        location=geo,
        regions=frozenset({usa_region(geo)}),
        description=description,
        url=item.get("url") or "",
        published_at=item.get("pubDate"),
        tags=tags,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=item.get("salaryCurrency") or None,
        salary_period="YEARLY" if (salary_min is not None or salary_max is not None) else None,
    )
