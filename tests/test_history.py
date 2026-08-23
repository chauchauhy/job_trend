from src.analysis import history
from src.analysis.skills import SkillStat


def _stat(name: str, count: int) -> SkillStat:
    return SkillStat(name=name, category="languages", count=count, pct=0.0, sample_titles=())


def test_roundtrip(tmp_path):
    history.record_snapshot("USA", 1000.0, 10, [_stat("Python", 5)], data_dir=tmp_path)
    history.record_snapshot("USA", 2000.0, 20, [_stat("Python", 9), _stat("Go", 2)], data_dir=tmp_path)
    snaps = history.load_history("USA", data_dir=tmp_path)
    assert [s["ts"] for s in snaps] == [1000.0, 2000.0]
    assert snaps[-1]["total"] == 20
    assert snaps[-1]["skills"] == {"Python": 9, "Go": 2}


def test_cap_trims_oldest(tmp_path):
    for i in range(history.MAX_SNAPSHOTS + 5):
        history.record_snapshot("Global", float(i), i, [], data_dir=tmp_path)
    snaps = history.load_history("Global", data_dir=tmp_path)
    assert len(snaps) == history.MAX_SNAPSHOTS
    assert snaps[0]["ts"] == 5.0
    assert snaps[-1]["ts"] == float(history.MAX_SNAPSHOTS + 4)


def test_missing_file_returns_empty(tmp_path):
    assert history.load_history("Hong Kong", data_dir=tmp_path) == []


def test_corrupt_file_returns_empty_and_recovers(tmp_path):
    (tmp_path / "history_hong_kong.json").write_text("{not json", encoding="utf-8")
    assert history.load_history("Hong Kong", data_dir=tmp_path) == []
    history.record_snapshot("Hong Kong", 1.0, 1, [_stat("Python", 1)], data_dir=tmp_path)
    snaps = history.load_history("Hong Kong", data_dir=tmp_path)
    assert len(snaps) == 1


def test_regions_use_separate_files(tmp_path):
    history.record_snapshot("USA", 1.0, 1, [], data_dir=tmp_path)
    history.record_snapshot("Hong Kong", 2.0, 1, [], data_dir=tmp_path)
    assert (tmp_path / "history_usa.json").exists()
    assert (tmp_path / "history_hong_kong.json").exists()
    assert len(history.load_history("USA", data_dir=tmp_path)) == 1
    assert len(history.load_history("Hong Kong", data_dir=tmp_path)) == 1
