from src.analysis.salary import (
    annualize,
    job_salary,
    median_text,
    money,
    normalize_title,
    parse_salary_text,
    range_text,
    region_salary,
    salary_breakdown,
    salary_to_usd,
    seniority_breakdown,
    seniority_of,
    skill_salary,
    source_salary,
)
from tests.helpers import make_job


def test_normalize_title_strips_seniority_and_parentheticals():
    assert normalize_title("Senior Software Engineer") == "Software Engineer"
    assert normalize_title("Staff Software Engineer") == "Software Engineer"
    assert normalize_title("Senior Staff Data Engineer") == "Data Engineer"
    assert normalize_title("Principal Platform Engineer (United States)") == "Platform Engineer"
    assert normalize_title("Full Stack Developer - Remote") == "Full Stack Developer"
    assert normalize_title("Backend Engineer") == "Backend Engineer"


def test_salary_breakdown_groups_and_computes_median():
    jobs = [
        make_job(job_id="1", title="Senior Backend Engineer", salary_min=100_000, salary_max=140_000, salary_currency="USD", salary_period="YEARLY"),
        make_job(job_id="2", title="Backend Engineer", salary_min=120_000, salary_max=160_000, salary_currency="USD", salary_period="YEARLY"),
        make_job(job_id="3", title="Backend Engineer"),
        make_job(job_id="4", title="Frontend Engineer", salary_min=90_000, salary_max=110_000, salary_currency="USD", salary_period="YEARLY"),
    ]
    rows = salary_breakdown(jobs)
    backend = next(r for r in rows if r.title == "Backend Engineer")
    assert backend.jobs == 3
    assert backend.with_salary == 2
    assert backend.salary_min == 100_000
    assert backend.salary_max == 160_000
    assert backend.median == 130_000
    front = next(r for r in rows if r.title == "Frontend Engineer")
    assert front.median == 100_000


def test_salary_breakdown_marks_mixed_currency_and_period():
    jobs = [
        make_job(job_id="1", title="Engineer", salary_min=100, salary_max=200, salary_currency="USD", salary_period="HOURLY"),
        make_job(job_id="2", title="Engineer", salary_min=5_000, salary_max=6_000, salary_currency="HKD", salary_period="MONTHLY"),
    ]
    row = salary_breakdown(jobs)[0]
    assert row.currency == "mixed"
    assert row.period == "mixed"
    assert row.with_salary == 2


def test_salary_breakdown_sort_priority():
    jobs = [
        make_job(job_id="1", title="Engineer", salary_min=100_000, salary_max=200_000, salary_currency="USD"),
        make_job(job_id="2", title="Designer"),
        make_job(job_id="3", title="Designer"),
    ]
    rows = salary_breakdown(jobs)
    assert rows[0].title == "Engineer"
    assert rows[1].title == "Designer"


def test_single_value_job_presents_min_max_equal():
    job = make_job(job_id="1", title="Support Eng", salary_min=50_000, salary_max=50_000, salary_currency="USD")
    rows = salary_breakdown([job])
    assert rows[0].salary_min == rows[0].salary_max == 50_000


def test_region_salary_uses_dominant_currency():
    jobs = [
        make_job(job_id="1", title="Eng A", salary_min=100, salary_max=200, salary_currency="USD", salary_period="YEARLY"),
        make_job(job_id="2", title="Eng B", salary_min=80_000, salary_max=100_000, salary_currency="HKD", salary_period="YEARLY"),
        make_job(job_id="3", title="Eng C", salary_min=90_000, salary_max=120_000, salary_currency="HKD", salary_period="YEARLY"),
        make_job(job_id="4", title="Eng D"),
    ]
    summary = region_salary(jobs)
    assert summary.with_salary == 2
    assert summary.currency == "HKD"
    assert summary.period == "YEARLY"
    assert summary.median == 97_500
    assert summary.salary_min == 80_000
    assert summary.salary_max == 120_000
    assert region_salary([make_job(job_id="5", title="Eng E")]).with_salary == 0


def test_region_salary_separates_periods():
    jobs = [
        make_job(job_id="1", title="Eng A", salary_min=100, salary_max=200, salary_currency="USD", salary_period="HOURLY"),
        make_job(job_id="2", title="Eng B", salary_min=120, salary_max=170, salary_currency="USD", salary_period="HOURLY"),
        make_job(job_id="3", title="Eng C", salary_min=100_000, salary_max=120_000, salary_currency="USD", salary_period="YEARLY"),
    ]
    summary = region_salary(jobs)
    assert summary.period == "HOURLY"
    assert summary.with_salary == 2
    assert summary.median == 306_800
    assert summary.salary_max == 416_000


def test_money_and_range_formatting():
    assert money(123_456, "USD") == "$123,456"
    assert money(123_456, "HKD") == "HKD 123,456"
    assert money(None) == "—"
    row = salary_breakdown(
        [make_job(job_id="1", title="Eng", salary_min=100_000, salary_max=180_000, salary_currency="USD")]
    )[0]
    assert range_text(row) == "$100,000–$180,000"
    assert median_text(row) == "$140,000"
    single = salary_breakdown(
        [make_job(job_id="2", title="Eng", salary_min=200_000, salary_max=200_000, salary_currency="USD")]
    )[0]
    assert range_text(single) == "$200,000"


def test_annualize_scales_periods():
    assert annualize(100, "HOURLY") == 208_000
    assert annualize(5_000, "MONTHLY") == 60_000
    assert annualize(10_000, "YEARLY") == 10_000
    assert annualize(10_000, None) == 10_000


def test_parse_salary_range_and_k_suffix():
    v = parse_salary_text("Compensation $31,2k- $52k", None)
    assert (v.min_value, v.max_value) == (31_200, 52_000)


def test_parse_salary_per_hour_period():
    v = parse_salary_text("Rate $120 - $170 /hour", None)
    assert (v.min_value, v.max_value) == (120, 170)
    assert v.period == "HOURLY"


def test_parse_salary_uk_symbol():
    v = parse_salary_text("£55,000–£70,000 per year", None)
    assert v.currency == "GBP"
    assert v.period == "YEARLY"


def test_parse_salary_ignores_funding_noise():
    assert parse_salary_text("Company raised $475M from investors", None) is None
    assert parse_salary_text("we paid $11M to builders", None) is None
    assert parse_salary_text("earn $85+ million from clients", None) is None
    assert parse_salary_text("$9 trillion in payment volume", None) is None


def test_parse_salary_single_requires_keyword_proximity():
    v = parse_salary_text("Salary range $140,000.", None)
    assert v is not None and v.min_value == 140_000
    assert parse_salary_text("great place to work, $300 stipend and equity", None) is None


def test_parse_salary_default_currency():
    v = parse_salary_text("月薪 $40,000 - $60,000 per month", "HKD")
    assert v.currency == "HKD"
    assert v.period == "MONTHLY"


def test_salary_to_usd():
    assert salary_to_usd(78_000, "HKD") == 10_000
    assert salary_to_usd(120_000, "USD") == 120_000


def test_job_salary_prefers_structured():
    job = make_job(salary_min=90_000, salary_max=110_000, salary_currency="USD", salary_period="YEARLY")
    v = job_salary(job)
    assert v.source == "api"
    assert v.max_value == 110_000


def test_job_salary_falls_back_to_description():
    job = make_job(description="The base salary range is $80,000 - $95,000 per year.")
    v = job_salary(job, "USD")
    assert v.source == "description"
    assert v.min_value == 80_000


def test_job_salary_none_without_salary():
    assert job_salary(make_job(description="No pay disclosed. Apply today!")) is None


def test_salary_breakdown_uses_description_and_annualizes():
    jobs = [
        make_job(job_id="1", title="Backend Engineer", description="Salary $100,000 - $140,000 per year"),
        make_job(job_id="2", title="Backend Engineer", description="Compensation $120,000 - $160,000 per year"),
        make_job(job_id="3", title="Backend Engineer", description="no pay"),
        make_job(job_id="4", title="Frontend Engineer", description="RATE $50 per hour"),
    ]
    rows = salary_breakdown(jobs, default_currency="USD")
    backend = next(r for r in rows if r.title == "Backend Engineer")
    assert backend.with_salary == 2
    assert backend.median_annual == 130_000
    assert backend.source == "description"
    front = next(r for r in rows if r.title == "Frontend Engineer")
    assert front.median_annual == 104_000


def test_salary_breakdown_drops_implausible():
    jobs = [make_job(job_id="1", title="Eng", description="Salary range $2,000,000 - $3,000,000 per year")]
    rows = salary_breakdown(jobs, default_currency="USD")
    assert rows and rows[0].with_salary == 0


def test_salary_breakdown_high_coverage_with_description():
    jobs = [
        make_job(job_id="1", title="Eng", description="Salary $80,000 - $95,000 per year"),
        make_job(job_id="2", title="Eng", description="No data"),
    ]
    rows = salary_breakdown(jobs, default_currency="USD")
    assert rows[0].with_salary == 1


def test_seniority_detection():
    assert seniority_of("Senior Backend Engineer") == "senior"
    assert seniority_of("Staff Engineer") == "staff"
    assert seniority_of("Lead Engineer") == "lead"
    assert seniority_of("Principal Engineer") == "principal"
    assert seniority_of("Junior Engineer") == "junior"
    assert seniority_of("Backend Engineer") == "other"


def test_seniority_breakdown():
    jobs = [
        make_job(job_id="1", title="Senior Engineer", description="Salary $120,000 per year"),
        make_job(job_id="2", title="Senior Architect", description="Salary $140,000 per year"),
        make_job(job_id="3", title="Engineer"),
    ]
    rows = seniority_breakdown(jobs, default_currency="USD")
    senior = next(r for r in rows if r["level"] == "senior")
    assert senior["jobs"] == 2 and senior["median"] == 130_000


def test_skill_salary_returns_top_by_count():
    from src.analysis.skills import SkillMatcher

    jobs = [
        make_job(job_id="1", title="Python Dev", description="python Salary $120,000 - $140,000 per year"),
        make_job(job_id="2", title="Full Stack", description="python Salary $110,000 - $130,000 per year"),
        make_job(job_id="3", title="Go Dev", description="go Salary $150,000 per year"),
    ]
    rows = skill_salary(jobs, SkillMatcher(), default_currency="USD")
    python = next(r for r in rows if r["skill"] == "Python")
    assert python["jobs"] == 2
    assert python["median"] == 125_000


def test_source_salary_grouping():
    jobs = [
        make_job(job_id="1", source="jobicy", description="Salary $90,000 per year"),
        make_job(job_id="2", source="remotive", description="Salary $100,000 per year"),
    ]
    rows = source_salary(jobs, default_currency="USD")
    assert {r["source"] for r in rows} == {"jobicy", "remotive"}
    assert next(r for r in rows if r["source"] == "jobicy")["median"] == 90_000