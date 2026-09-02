import pytest

from src.chat.handler import respond, resolve_region, resolve_regions
from tests.helpers import make_job


@pytest.fixture
def store():
    jobs = [
        make_job(job_id="h1", title="Python Developer", description="django react python"),
        make_job(job_id="h2", title="Java Engineer", description="spring boot java"),
    ]
    usa = [make_job(job_id="u1", title="React Dev", description="react typescript")]
    return {"Hong Kong": jobs, "USA": usa, "_stats_Hong Kong": None, "_stats_USA": None}


def test_resolve_region_aliases():
    assert resolve_region("python jobs in hk please") == "Hong Kong"
    assert resolve_region("compare usa vs global") == "USA"
    assert resolve_region("no region here") is None


def test_resolve_regions_returns_all_mentions_in_order():
    assert resolve_regions("compare hk vs usa vs hk again") == ["Hong Kong", "USA"]


def test_help_intent(store):
    text, df = respond("help", "Hong Kong", store)
    assert "What you can ask" in text
    assert df is None


def test_top_skills_intent_uses_cached_stats(store):
    text, df = respond("what are the top skills?", "Hong Kong", store)
    assert "Top skills in Hong Kong" in text
    assert df is not None and not df.empty
    assert set(df.columns) == {"skill", "category", "jobs", "%"}
    assert "_stats_Hong Kong" in store and store["_stats_Hong Kong"]


def test_skill_lookup_intent(store):
    text, df = respond("how often is python required?", "Hong Kong", store)
    assert "**Python**" in text
    assert "1/2" in text


def test_unknown_skill(store):
    text, _ = respond("cobol jobs?", "Hong Kong", store)
    assert "doesn't appear" in text


def test_compare_named_pair_only(store):
    text, df = respond("compare hk vs usa", "Global", store)
    assert "Hong Kong vs USA" in text
    cols = set(df.columns)
    assert "Hong Kong jobs" in cols and "Hong Kong %" in cols
    assert "USA jobs" in cols and "USA %" in cols
    assert "Global jobs" not in cols


def test_compare_missing_region_reports_missing(store):
    text, df = respond("compare hk vs global", "Hong Kong", store)
    assert "refresh" in text.lower()
    assert df is None


def test_empty_region_prompts_refresh(store):
    text, _ = respond("top skills", "Global", store)
    assert "No jobs cached" in text


def test_fallback_suggests_help(store):
    text, _ = respond("hello there friend", "Hong Kong", store)
    assert "help" in text.lower()


def _salary_store():
    jobs = [
        make_job(
            job_id="h1",
            title="Python Developer",
            description="Build APIs. Salary range $120,000 - $140,000 per year.",
        ),
        make_job(
            job_id="h2",
            title="Senior Backend Engineer",
            description="Go and Python. Compensation $150,000 - $170,000 per year.",
        ),
        make_job(job_id="h3", title="Java Engineer", description="No pay disclosed here."),
    ]
    return {"Hong Kong": jobs}


def test_salary_by_skill_intent():
    store = _salary_store()
    text, df = respond("salary python", "Hong Kong", store)
    assert df is not None
    assert "Python" in text


def test_salary_highest_paying_intent():
    store = _salary_store()
    text, df = respond("highest paying titles", "Hong Kong", store)
    assert df is not None
    assert df.iloc[0]["title"] == "Backend Engineer"


def test_salary_by_title_intent():
    store = _salary_store()
    text, df = respond("salary by title", "Hong Kong", store)
    assert df is not None
    assert set(df.columns) >= {"title", "with salary", "median (yr)"}


def test_salary_coverage_intent():
    store = _salary_store()
    text, df = respond("salary coverage", "Hong Kong", store)
    assert df is None
    assert "2/3" in text


def test_compare_salary_intent():
    usa = [
        make_job(job_id="u1", title="React Dev", description="Salary range $90,000 - $110,000 per year."),
    ]
    store = {"Hong Kong": _salary_store()["Hong Kong"], "USA": usa}
    text, df = respond("compare salary hk vs usa", "Global", store)
    assert df is not None
    assert set(df.columns) >= {"region", "with salary", "median"}
