from src.analysis import gap
from src.analysis.skills import get_matcher


def test_normalize_dedupes_case_and_whitespace():
    matcher = get_matcher()
    known = set(matcher.patterns)
    target = next(iter(sorted(known)))
    out = gap.normalize_skills([f"  {target} ", target.upper(), target], matcher)
    assert out == [target]


def test_normalize_drops_unknown_and_empty():
    matcher = get_matcher()
    known = set(matcher.patterns)
    out = gap.normalize_skills(["", "   ", "zzzqqqxx"], matcher)
    assert out == []
    for name in gap.normalize_skills(["zzzqqqxx", next(iter(known))], matcher):
        assert name in known


def test_roundtrip(tmp_path):
    assert gap.load_own_skills(data_dir=tmp_path) == []
    gap.save_own_skills(["Python", "Go"], data_dir=tmp_path)
    assert gap.load_own_skills(data_dir=tmp_path) == ["Python", "Go"]


def test_corrupt_file_returns_empty(tmp_path):
    (tmp_path / "my_skills.json").write_text("[broken", encoding="utf-8")
    assert gap.load_own_skills(data_dir=tmp_path) == []
