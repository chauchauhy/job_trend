from src.sources import base
from src.sources.base import get_json, usa_region
from src.sources.jsearch import _to_job as jsearch_to_job
from src.sources.remoteok import _to_job as remoteok_to_job


def test_get_json_maps_connection_error(monkeypatch):
    def raise_conn(*args, **kwargs):
        raise base.requests.ConnectionError("boom")

    monkeypatch.setattr(base.requests, "request", raise_conn)
    data, error = get_json("https://example.com/api")
    assert data is None and error == "connection error"


def test_get_json_maps_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise base.requests.Timeout("slow")

    monkeypatch.setattr(base.requests, "request", raise_timeout)
    data, error = get_json("https://example.com/api")
    assert data is None and error == "timeout"


def test_get_json_maps_unexpected_request_exception(monkeypatch):
    def raise_other(*args, **kwargs):
        raise base.requests.RequestException("weird")

    monkeypatch.setattr(base.requests, "request", raise_other)
    data, error = get_json("https://example.com/api")
    assert data is None and error == "RequestException"


def test_usa_region_detection():
    assert usa_region("USA only") == "USA"
    assert usa_region("Remote - United States") == "USA"
    assert usa_region("Worldwide") == "Global"
    assert usa_region("") == "Global"
    assert usa_region(None) == "Global"


def test_jsearch_mapping():
    job = jsearch_to_job(
        {
            "job_id": "abc123",
            "job_title": "Senior Python Engineer",
            "employer_name": "BigCo",
            "job_city": "Kowloon",
            "job_country": "HK",
            "job_description": "<p>Build <b>APIs</b></p>",
            "job_apply_link": "https://jobs.example/1",
            "job_posted_at_datetime_utc": "2026-08-01T00:00:00Z",
            "job_required_skills": ["Python", "Django", "SQL"],
        },
        "Hong Kong",
    )
    assert job.id == "jsearch:abc123"
    assert job.source == "jsearch"
    assert job.title == "Senior Python Engineer"
    assert job.company == "BigCo"
    assert "Kowloon" in job.location and "HK" in job.location
    assert job.regions == frozenset({"Hong Kong"})
    assert job.description == "Build APIs"
    assert job.tags == ("Python", "Django", "SQL")
    assert job.url == "https://jobs.example/1"


def test_jsearch_skills_string_form():
    job = jsearch_to_job({"job_id": "x", "job_title": "Dev", "job_required_skills": "Go, K8s ,"}, "USA")
    assert job.tags == ("Go", "K8s")


def test_remoteok_skips_notice_and_maps():
    from src.sources.remoteok import fetch as _unused  # noqa: F401  import check only

    from src.sources import remoteok

    class FakeResp:
        pass

    notice = {"legal": "do not scrape", "slug": ""}
    payload = [
        notice,
        {
            "id": 99,
            "position": "Backend Dev",
            "company": "RemoteCo",
            "location": "USA",
            "tags": ["Python", "AWS"],
            "description": "<h1>Job</h1><p>Body</p>",
            "url": "https://remoteok.com/remote-jobs/99",
            "date": "2026-08-20",
        },
        {"not": "a job"},
    ]

    def fake_get_json(url):
        return payload, None

    original = remoteok.get_json
    remoteok.get_json = fake_get_json
    try:
        jobs, error = remoteok.fetch()
    finally:
        remoteok.get_json = original
    assert error is None
    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "remoteok:99"
    assert job.source == "remoteok"
    assert job.title == "Backend Dev"
    assert job.regions == frozenset({"USA"})
    assert job.description.startswith("Job Body") or "Job" in job.description
    assert job.tags == ("Python", "AWS")


def test_remoteok_error_passthrough(monkeypatch):
    from src.sources import remoteok

    monkeypatch.setattr(remoteok, "get_json", lambda url: (None, "HTTP 403"))
    jobs, error = remoteok.fetch()
    assert jobs == [] and error == "HTTP 403"
