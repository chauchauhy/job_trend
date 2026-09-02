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
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_period: str | None = None


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
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
        salary_currency=data.get("salary_currency"),
        salary_period=data.get("salary_period"),
    )
