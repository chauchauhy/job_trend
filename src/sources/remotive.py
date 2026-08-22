from config import settings
from src.models import Job
from src.sources.base import get_json, strip_html, usa_region


def fetch() -> tuple[list[Job], str | None]:
    data, error = get_json(
        settings.api.remotive_url,
        params={"category": "software-dev"},
    )
    if error:
        return [], error
    items = data.get("jobs", []) if isinstance(data, dict) else []
    return [_to_job(item) for item in items if item.get("title")], None


def _to_job(item: dict) -> Job:
    location = str(item.get("candidate_required_location") or "")
    tags = tuple(t.strip() for t in (item.get("tags") or []) if t and t.strip())
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
    )
