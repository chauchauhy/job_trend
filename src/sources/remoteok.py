from config import settings
from src.models import Job
from src.sources.base import get_json, strip_html, usa_region


def fetch() -> tuple[list[Job], str | None]:
    data, error = get_json(settings.api.remoteok_url)
    if error:
        return [], error
    if not isinstance(data, list):
        return [], "unexpected response shape"
    jobs = [_to_job(item) for item in data if isinstance(item, dict) and item.get("position")]
    return jobs, None


def _to_job(item: dict) -> Job:
    location = str(item.get("location") or "")
    tags = tuple(str(t).strip() for t in (item.get("tags") or []) if t and str(t).strip())
    job_id = item.get("id") or item.get("slug") or ""
    return Job(
        id=f"remoteok:{job_id}",
        source="remoteok",
        title=str(item["position"]),
        company=item.get("company") or "",
        location=location,
        regions=frozenset({usa_region(location)}),
        description=strip_html(item.get("description")),
        url=item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('slug', '')}",
        published_at=item.get("date"),
        tags=tags[:15],
    )
