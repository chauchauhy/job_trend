from src.models import Job


def make_job(
    job_id: str = "j1",
    source: str = "jobicy",
    title: str = "Backend Engineer",
    company: str = "Acme",
    location: str = "",
    regions: tuple[str, ...] = ("Global",),
    description: str = "",
    url: str = "",
    tags: tuple[str, ...] = (),
) -> Job:
    return Job(
        id=job_id,
        source=source,
        title=title,
        company=company,
        location=location,
        regions=frozenset(regions),
        description=description,
        url=url,
        published_at=None,
        tags=tags,
    )
