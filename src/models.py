from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Job:
    id: str
    source: str
    title: str
    company: str
    location: str
    regions: frozenset[str]
    description: str
    url: str
    published_at: str | None
    tags: tuple[str, ...]


def job_to_dict(job: Job) -> dict:
    data = asdict(job)
    data["regions"] = sorted(job.regions)
    return data


def job_from_dict(data: dict) -> Job:
    return Job(
        id=data["id"],
        source=data["source"],
        title=data["title"],
        company=data.get("company", ""),
        location=data.get("location", ""),
        regions=frozenset(data.get("regions", [])),
        description=data.get("description", ""),
        url=data.get("url", ""),
        published_at=data.get("published_at"),
        tags=tuple(data.get("tags", ())),
    )
