from src.sources import base
from src.sources.base import get_json, salary_int, usa_region
from src.sources.jobicy import _to_job as jobicy_to_job
from src.sources.jsearch import _to_job as jsearch_to_job
from src.sources.remotive import _parse_salary
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


def test_salary_int_coercion():
    assert salary_int(None) is None
    assert salary_int(0) == 0
    assert salary_int(75_000) == 75_000
    assert salary_int("120,000") == 120_000
    assert salary_int("90.5") == 90
    assert salary_int(True) is None
    assert salary_int("unknown") is None
    assert salary_int("") is None


def test_jsearch_maps_salary_fields():
    job = jsearch_to_job(
        {
            "job_id": "s1",
            "job_title": "Data Engineer",
            "job_required_skills": ["SQL"],
            "job_min_salary": "100000",
            "job_max_salary": "150000",
            "job_salary_currency": "USD",
            "job_salary_period": "YEARLY",
        },
        "USA",
    )
    assert job.salary_min == 100_000
    assert job.salary_max == 150_000
    assert job.salary_currency == "USD"
    assert job.salary_period == "YEARLY"


def test_jsearch_defaults_currency_and_normalizes_period():
    job = jsearch_to_job(
        {
            "job_id": "s3",
            "job_title": "Dev",
            "job_min_salary": "100000",
            "job_max_salary": "150000",
            "job_salary_period": "YEAR",
        },
        "USA",
    )
    assert job.salary_currency == "USD"
    assert job.salary_period == "YEARLY"
    job_hk = jsearch_to_job(
        {"job_id": "s4", "job_title": "Dev", "job_min_salary": "30000", "job_max_salary": "60000"},
        "Hong Kong",
    )
    assert job_hk.salary_currency == "HKD"


def test_jsearch_absent_salary_is_none():
    job = jsearch_to_job({"job_id": "s2", "job_title": "Dev"}, "USA")
    assert job.salary_min is None and job.salary_max is None
    assert job.salary_currency is None and job.salary_period is None


def test_jobicy_maps_annual_salary():
    job = jobicy_to_job(
        {
            "id": 7,
            "jobTitle": "Cloud Engineer",
            "jobGeo": "USA",
            "jobIndustry": ["Engineering"],
            "annualSalaryMin": 90000,
            "annualSalaryMax": 130000,
            "salaryCurrency": "USD",
        }
    )
    assert job.salary_min == 90_000
    assert job.salary_max == 130_000
    assert job.salary_currency == "USD"
    assert job.salary_period == "YEARLY"


def test_jobicy_without_salary_has_no_period():
    job = jobicy_to_job({"id": 8, "jobTitle": "Dev", "jobGeo": "Worldwide"})
    assert job.salary_min is None and job.salary_max is None
    assert job.salary_period is None


def test_remotive_parses_salary_range():
    jobicy_remotive = {
        "id": 9,
        "title": "Backend Dev",
        "description": "Body",
        "salary": "$150,000 - $180,000",
    }
    from src.sources import remotive

    job = remotive._to_job(jobicy_remotive)
    assert job.salary_min == 150_000
    assert job.salary_max == 180_000
    assert job.salary_currency == "USD"
    assert job.salary_period == "YEARLY"


def test_remotive_parses_single_and_periods():
    low, high, cur, period = _parse_salary("$40 per hour")
    assert (low, high, cur, period) == (40, 40, "USD", "HOURLY")
    low, high, cur, period = _parse_salary("4,500 € / month")
    assert (low, high, cur, period) == (4_500, 4_500, "EUR", "MONTHLY")
    low, high, cur, period = _parse_salary("Competitive")
    assert (low, high, cur) == (None, None, None)


def test_remotive_parses_hour_slash_and_k_suffix():
    low, high, cur, period = _parse_salary("$120 - $170 /hour")
    assert (low, high, cur, period) == (120, 170, "USD", "HOURLY")
    low, high, cur, period = _parse_salary("$31,2k- $52k")
    assert (low, high, cur, period) == (31_200, 52_000, "USD", "YEARLY")


def test_remotive_salary_symbol_currency():
    low, high, cur, period = _parse_salary("£55,000–£70,000 per year")
    assert (low, high, cur, period) == (55_000, 70_000, "GBP", "YEARLY")


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
