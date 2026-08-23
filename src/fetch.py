import json
import re
import time
from collections import Counter

from config import JSEARCH_REGIONS, REMOTE_SOURCES_REGIONS, settings
from src.analysis.history import record_snapshot
from src.analysis.skills import SkillStat, compute_stats
from src.models import Job, job_from_dict, job_to_dict
from src.sources import jobicy, jsearch, remoteok, remotive

_DESC_PREVIEW_CHARS = 600
_KEYWORDS_MTIME: float | None = None
_RELEVANCE_PATTERN: re.Pattern[str] | None = None


def pull_and_record(
    region: str, *, data_dir=None
) -> tuple[list[Job], list[SkillStat], list[str]]:
    jobs, warnings = refresh_region(region)
    stats = compute_stats(jobs) if jobs else []
    if jobs:
        record_snapshot(region, time.time(), len(jobs), stats, data_dir=data_dir)
    return jobs, stats, warnings


def refresh_region(region: str) -> tuple[list[Job], list[str]]:
    warnings: list[str] = []
    keywords = _load_keywords()
    merged: dict[str, Job] = {}

    has_jsearch = bool(settings.api.jsearch_api_key)

    if region == "Hong Kong" and not has_jsearch:
        warnings.append("Add JSEARCH_API_KEY to .env to pull Hong Kong (free at app.openwebninja.com/api/jsearch).")

    if region in JSEARCH_REGIONS and has_jsearch:
        js_jobs, js_error = jsearch.fetch(keywords["search_queries"], region)
        if js_error and "403" in js_error:
            warnings.append(f"JSearch rejected the key ({js_error}) — confirm the OpenWeb Ninja plan is active.")
        elif js_error:
            warnings.append(f"JSearch request failed ({js_error}).")
        elif not js_jobs:
            warnings.append("JSearch matched nothing for the configured keywords.")
        _merge(merged, js_jobs)

    if region in REMOTE_SOURCES_REGIONS:
        for label, fetch_remote in (
            ("Jobicy", jobicy.fetch),
            ("Remotive", remotive.fetch),
            ("RemoteOK", remoteok.fetch),
        ):
            jobs, error = fetch_remote()
            if error:
                warnings.append(f"{label} feed unreachable ({error}).")
            elif not jobs:
                warnings.append(f"{label} feed was empty.")
            _merge(merged, jobs)

    pool = _filter_by_region(merged.values(), region)
    relevant = [job for job in pool if _is_relevant(job)]
    dropped = len(pool) - len(relevant)
    if dropped:
        warnings.append(f"Filtered out {dropped} off-topic listings.")
    if not relevant and pool:
        warnings.append(
            "Relevance filter kept nothing — loosen relevance_terms in res/config/keywords.json."
        )

    relevant.sort(key=lambda j: (j.source != "jsearch", j.title.lower()))
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
