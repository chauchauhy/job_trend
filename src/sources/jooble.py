import time

from config import REGIONS, settings
from src.models import Job
from src.sources.base import post_json, strip_html


def fetch(keywords: list[str], region: str) -> tuple[list[Job], str | None]:
    api_key = settings.api.jooble_api_key
    if not api_key:
        return [], None
    location = REGIONS[region]
    jobs: dict[str, Job] = {}
    errors: dict[str, int] = {}
    for keyword in keywords:
        for page in range(1, settings.fetch.jooble_max_pages_per_keyword + 1):
            payload: dict[str, object] = {"keywords": keyword, "page": page}
            if location:
                payload["location"] = location
            data, error = post_json(f"{settings.api.jooble_base_url}/{api_key}", payload)
            if error:
                errors[error] = errors.get(error, 0) + 1
                break
            items = data.get("jobs", []) if isinstance(data, dict) else []
            if not items:
                break
            for item in items:
                job = _to_job(item, region)
                jobs.setdefault(job.id, job)
            time.sleep(settings.fetch.request_delay_s)
    error_summary = ", ".join(f"{msg} x{count}" for msg, count in sorted(errors.items()))
    return list(jobs.values()), error_summary or None


def _to_job(item: dict, region: str) -> Job:
    return Job(
        id=f"jooble:{item.get('id', '')}",
        source="jooble",
        title=item.get("title") or "",
        company=item.get("company") or "",
        location=item.get("location") or "",
        regions=frozenset({region}),
        description=strip_html(item.get("snippet")),
        url=item.get("link") or "",
        published_at=item.get("updated"),
        tags=(),
    )
