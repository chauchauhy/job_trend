import src.fetch as fetch_mod
from src.models import job_from_dict, job_to_dict
from tests.helpers import make_job


def test_region_filter_keeps_usa_only_for_usa_target():
    pool = [
        make_job(job_id="a", regions=("USA",)),
        make_job(job_id="b", regions=("Global",)),
        make_job(job_id="c", regions=("Hong Kong",)),
    ]
    kept = fetch_mod._filter_by_region(pool, "USA")
    assert [j.id for j in kept] == ["a"]
    assert len(fetch_mod._filter_by_region(pool, "Global")) == 3


def test_relevance_uses_title_tags_and_description_window():
    by_title = make_job(job_id="t1", title="Senior Python Developer")
    by_tags = make_job(job_id="t2", title="Hiring now", tags=("Software Engineering",))
    by_desc = make_job(
        job_id="t3",
        title="Join our team",
        description="You will join a software developer team building APIs. " + "filler " * 200,
    )
    off_topic_deep = make_job(
        job_id="t4",
        title="Sales Manager",
        description="Sell widgets. " + "x" * 700 + " mention of programmer far beyond window",
    )
    off_topic = make_job(job_id="t5", title="Account Executive", description="quota and cold calls")

    for job in (by_title, by_tags, by_desc):
        assert fetch_mod._is_relevant(job), job.id
    for job in (off_topic_deep, off_topic):
        assert not fetch_mod._is_relevant(job), job.id


def test_dedupe_by_url_then_title_company():
    merged: dict = {}
    first = make_job(job_id="1", url="https://x.io/job/1?utm=spam")
    second = make_job(job_id="2", url="https://X.io/job/1")
    third = make_job(job_id="3", title="Same Title", company="Acme")
    fourth = make_job(job_id="4", title="same title", company="acme")
    for job in (first, second, third, fourth):
        fetch_mod._merge(merged, [job])
    assert len(merged) == 2


def test_disk_cache_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch_mod, "cache_path", lambda region: tmp_path / "usa.json")
    jobs = [
        make_job(job_id="r1", regions=("USA", "Global"), tags=("QA & Testing",)),
        make_job(job_id="r2", source="jobicy", regions=("USA",)),
    ]
    fetch_mod.save_cache("USA", jobs, fetched_at=1234.5)
    loaded = fetch_mod.load_cached("USA")
    assert loaded is not None
    restored, fetched_at, schema_version = loaded
    assert fetched_at == 1234.5
    assert schema_version == fetch_mod.CACHE_SCHEMA_VERSION
    assert restored == jobs
    assert restored[0].regions == frozenset({"USA", "Global"})


def test_legacy_cache_without_schema_version_is_stale(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(fetch_mod, "cache_path", lambda region: tmp_path / "usa.json")
    path = tmp_path / "usa.json"
    path.write_text(json.dumps({"fetched_at": 1.0, "jobs": []}), encoding="utf-8")
    loaded = fetch_mod.load_cached("USA")
    assert loaded is not None
    _jobs, _fetched_at, schema_version = loaded
    assert schema_version == 1
    assert not fetch_mod.cache_schema_current(schema_version)


def test_current_schema_version_is_fresh():
    assert fetch_mod.cache_schema_current(fetch_mod.CACHE_SCHEMA_VERSION)


def test_pull_and_record_stores_salary_payload(monkeypatch, tmp_path):
    from src.analysis import history

    job = make_job(job_id="p1", description="Salary $90,000 - $110,000 per year")
    monkeypatch.setattr(fetch_mod, "refresh_region", lambda region: ([job], []))
    jobs, _stats, _warns = fetch_mod.pull_and_record("USA", data_dir=tmp_path)
    assert len(jobs) == 1
    snaps = history.load_history("USA", data_dir=tmp_path)
    assert snaps[-1]["salary"]["median_annual"] == 100_000
    assert snaps[-1]["salary"]["with_salary"] == 1


def test_serialization_preserves_frozenset_and_tuples():
    job = make_job(regions=("USA",), tags=("a", "b"))
    clone = job_from_dict(job_to_dict(job))
    assert clone == job


def test_refresh_region_calls_jsearch_only_when_key_present(monkeypatch):
    """jsearch must be skipped entirely when no API key is configured."""
    from config import ApiConfig, Settings

    calls: list[str] = []
    monkeypatch.setattr(fetch_mod, "save_cache", lambda *a, **k: None)

    def fake_jsearch(keywords, region):
        calls.append(region)
        return [], None

    monkeypatch.setattr(fetch_mod.jsearch, "fetch", fake_jsearch)
    for name in ("jobicy", "remotive", "remoteok"):
        monkeypatch.setattr(getattr(fetch_mod, name), "fetch", lambda: ([], None))

    monkeypatch.setattr(fetch_mod, "settings", Settings(api=ApiConfig(jsearch_api_key="")))
    fetch_mod.refresh_region("USA")
    assert calls == []

    monkeypatch.setattr(fetch_mod, "settings", Settings(api=ApiConfig(jsearch_api_key="key")))
    fetch_mod.refresh_region("USA")
    assert calls == ["USA"]


def test_refresh_hk_without_key_warns_and_never_calls_jsearch(monkeypatch):
    from config import ApiConfig, Settings

    monkeypatch.setattr(fetch_mod, "settings", Settings(api=ApiConfig(jsearch_api_key="")))
    monkeypatch.setattr(fetch_mod, "save_cache", lambda *a, **k: None)
    jobs, warnings = fetch_mod.refresh_region("Hong Kong")
    assert jobs == []
    assert any("JSEARCH_API_KEY" in w for w in warnings)
