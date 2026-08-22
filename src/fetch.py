import json
import re
import time
from collections import Counter

from config import JSEARCH_COUNTRY, REMOTE_SOURCES_REGIONS, settings
from src.models import Job, job_from_dict, job_to_dict
from src.sources import jobicy, jooble, jsearch, remoteok, remotive

_DESC_PREVIEW_CHARS = 600
_KEYWORDS_MTIME: float | None = None
_RELEVANCE_PATTERN: re.Pattern[str] | None = None


def refresh_region(region: str) -> tuple[list[Job], list[str]]:
    warnings: list[str] = []
    keywords = _load_keywords()
    merged: dict[str, Job] = {}

    has_jooble = bool(settings.api.jooble_api_key)
    has_jsearch = bool(settings.api.jsearch_api_key)

    if region == "Hong Kong" and not (has_jooble or has_jsearch):
        warnings.append("Hong Kong needs JOOBLE_API_KEY or JSEARCH_API_KEY in .env.")

    if has_jooble:
        jooble_jobs, jooble_error = jooble.fetch(keywords["search_queries"], region)
        if jooble_error:
            warnings.append(f"Jooble failed ({jooble_error}) — check your key at jooble.org/api.")
        elif not jooble_jobs:
            warnings.append("Jooble returned no matches for the configured keywords.")
        _merge(merged, jooble_jobs)

    if region in JSEARCH_COUNTRY and has_jsearch:
        js_jobs, js_error = jsearch.fetch(keywords["search_queries"], region)
        if js_error:
            warnings.append(f"JSearch failed ({js_error}).")
        elif not js_jobs:
            warnings.append("JSearch returned no matches for the configured keywords.")
        _merge(merged, js_jobs)

    if region in REMOTE_SOURCES_REGIONS:
        for label, fetch_remote in (
            ("Jobicy", jobicy.fetch),
            ("Remotive", remotive.fetch),
            ("RemoteOK", remoteok.fetch),
        ):
            jobs, error = fetch_remote()
            if error:
                warnings.append(f"{label} failed ({error}).")
            elif not jobs:
                warnings.append(f"{label} returned no jobs.")
            _merge(merged, jobs)

    pool = _filter_by_region(merged.values(), region)
    relevant = [job for job in pool if _is_relevant(job)]
    dropped = len(pool) - len(relevant)
    if dropped:
        warnings.append(f"Dropped {dropped} off-topic listings (title/tags/description match required).")
    if not relevant and pool:
        warnings.append(
            "Relevance filter kept nothing — loosen relevance_terms in res/config/keywords.json."
        )

    relevant.sort(key=lambda j: (j.source != "jooble", j.title.lower()))
    selected = relevant[: settings.fetch.max_jobs_per_region]
    fetched_at = time.time()
    save_cache(region, selected, fetched_at)
    return selected, warnings


def load_cached(region: str) -> tuple[list[Job], float] | None:
    path = cache_path(region)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding=settings.data.encoding))
        jobs = [job_from_dict(d) for d in raw["jobs"]]
        return jobs, float(raw["fetched_at"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_cache(region: str, jobs: list[Job], fetched_at: float) -> None:
    settings.paths.data.mkdir(parents=True, exist_ok=True)
    payload = {"fetched_at": fetched_at, "jobs": [job_to_dict(j) for j in jobs]}
    cache_path(region).write_text(
        json.dumps(payload, ensure_ascii=False), encoding=settings.data.encoding
    )


def cache_path(region: str):
    slug = region.lower().replace(" ", "_")
    return settings.paths.data / f"{slug}.json"


def cache_is_fresh(fetched_at: float | None) -> bool:
    if fetched_at is None:
        return False
    return (time.time() - fetched_at) < settings.fetch.cache_ttl_hours * 3600


def source_counts(jobs: list[Job]) -> Counter[str]:
    return Counter(job.source for job in jobs)


def _filter_by_region(jobs, region: str) -> list[Job]:
    if region == "Global":
        return list(jobs)
    return [job for job in jobs if region in job.regions]


def _merge(target: dict[str, Job], jobs: list[Job]) -> None:
    for job in jobs:
        target.setdefault(_dedupe_key(job), job)


def _dedupe_key(job: Job) -> str:
    if job.url:
        return "url:" + job.url.split("?")[0].rstrip("/").lower()
    return f"{job.title.strip().lower()}|{job.company.strip().lower()}"


def _is_relevant(job: Job) -> bool:
    pattern = _relevance_pattern(_load_keywords())
    headline = " ".join((job.title, *job.tags)).lower()
    if pattern.search(headline):
        return True
    preview = job.description[:_DESC_PREVIEW_CHARS].lower()
    return bool(pattern.search(preview))


def _relevance_pattern(keywords: dict) -> re.Pattern[str]:
    global _KEYWORDS_MTIME, _RELEVANCE_PATTERN
    path = settings.paths.config / "keywords.json"
    mtime = path.stat().st_mtime
    if _RELEVANCE_PATTERN is None or mtime != _KEYWORDS_MTIME:
        terms = sorted(set(keywords["relevance_terms"]), key=len, reverse=True)
        body = "|".join(re.escape(term) for term in terms)
        _RELEVANCE_PATTERN = re.compile(rf"(?<![a-z0-9])(?:{body})(?![a-z0-9])")
        _KEYWORDS_MTIME = mtime
    return _RELEVANCE_PATTERN


def _load_keywords() -> dict:
    path = settings.paths.config / "keywords.json"
    with open(path, encoding=settings.data.encoding) as fh:
        return json.load(fh)
