import importlib.util
import os
from pathlib import Path

import pytest

from config import REGIONS
from src.analysis import history
from src.models import Job

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "update_history.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("update_history", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _job(n: int = 1) -> Job:
    return Job(
        id=f"x{n}",
        source="stub",
        title=f"Engineer {n}",
        company="C",
        location="L",
        regions=frozenset({"USA"}),
        description="d",
        url="u",
        published_at=None,
        tags=(),
    )


@pytest.fixture
def isolated_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_TREND_DATA_DIR", str(tmp_path))
    return tmp_path


def test_pull_writes_snapshot(monkeypatch, isolated_dir):
    import src.fetch as fetch_module

    monkeypatch.setattr(fetch_module, "refresh_region", lambda region: ([_job()], []))
    script = _load_script()
    assert script.main(["--regions", "hk"]) == 0
    snaps = history.load_history("Hong Kong", data_dir=isolated_dir)
    assert len(snaps) == 1
    assert snaps[0]["total"] == 1


def test_empty_pull_skips_snapshot(monkeypatch, isolated_dir):
    import src.fetch as fetch_module

    monkeypatch.setattr(fetch_module, "refresh_region", lambda region: ([], ["feed down"]))
    script = _load_script()
    assert script.main(["--regions", "global"]) == 0
    assert history.load_history("Global", data_dir=isolated_dir) == []


def test_failure_isolated_and_exit_code(monkeypatch, isolated_dir):
    import src.fetch as fetch_module

    def flaky(region):
        if region == "USA":
            raise RuntimeError("network down")
        return [_job()], []

    monkeypatch.setattr(fetch_module, "refresh_region", flaky)
    script = _load_script()
    assert script.main([]) == 1
    assert len(history.load_history("Hong Kong", data_dir=isolated_dir)) == 1


def test_resolve_regions_aliases_and_default():
    script = _load_script()
    assert script.resolve_regions("hk, usa") == ["Hong Kong", "USA"]
    assert script.resolve_regions(None) == list(REGIONS)
    assert script.resolve_regions("bogus,hk") == ["Hong Kong"]
