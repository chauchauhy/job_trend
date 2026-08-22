from src.analysis.skills import compute_stats, get_matcher, lookup_skill, top_skills
from tests.helpers import make_job


def test_dangerous_aliases_no_longer_match():
    matcher = get_matcher()
    assert "Machine Learning" not in matcher.find_in_text("we apply ml daily")
    assert "Computer Vision" not in matcher.find_in_text("cv attached below")
    assert "Deep Learning" not in matcher.find_in_text("dl requirements")
    assert "Express.js" not in matcher.find_in_text("express delivery of features")
    assert "Spring Boot" not in matcher.find_in_text("spring is coming")
    assert "Oracle Database" not in matcher.find_in_text("oracle corporation office")
    assert "Android Development" not in matcher.find_in_text("android vibes")


def test_specific_terms_still_match():
    matcher = get_matcher()
    hits = matcher.find_in_text("Python, React and Kubernetes on AWS with Node.js")
    assert {"Python", "React", "Kubernetes", "AWS", "Node.js"} <= hits


def test_alias_still_matches_when_specific():
    matcher = get_matcher()
    assert "Node.js" in matcher.find_in_text("event loop via node runtime")
    assert "Oracle Database" in matcher.find_in_text("oracle db 19c administration")
    assert "NumPy" in matcher.find_in_text("numpy arrays everywhere")


def test_title_hit_scores_double():
    title_only = make_job(title="Python Developer", description="meetings and docs")
    body_only = make_job(job_id="j2", title="Platform Engineer", description="python tooling inside")
    stats = compute_stats([title_only, body_only])
    by_name = {s.name: s for s in stats}
    assert by_name["Python"].count == 2
    assert by_name["Python"].score == 3
    ranked = [s.name for s in stats]
    top_two = set(ranked[:2])
    assert "Python" in top_two


def test_top_skills_honors_top_n_and_category():
    jobs = [
        make_job(job_id=f"j{i}", title=f"Dev {i}", description="python java react aws docker linux git sql")
        for i in range(8)
    ]
    stats = compute_stats(jobs)
    assert len(top_skills(stats, top_n=3)) == 3
    limited = top_skills(stats, top_n=100, category="cloud_devops")
    assert all(s.category == "cloud_devops" for s in limited)


def test_lookup_skill_case_insensitive_substring():
    jobs = [make_job(description="deep python work")]
    stats = compute_stats(jobs)
    assert lookup_skill(stats, "PYTHON") is not None
    assert lookup_skill(stats, "zzz") is None
