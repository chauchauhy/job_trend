import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import src.fetch as fetch_module
from tests.helpers import make_job

_MAIN = str(Path(__file__).resolve().parents[1] / "main.py")

_REFRESH_LABEL = "⟳ Refresh"

_STUB_JOBS = [
    make_job(job_id="smoke1", title="Python Engineer", salary_min=100_000, salary_max=120_000, salary_currency="USD"),
    make_job(job_id="smoke2", title="React Engineer"),
]


@pytest.fixture(autouse=True)
def _stub_refresh_region(monkeypatch):
    monkeypatch.setattr(fetch_module, "refresh_region", lambda region: (_STUB_JOBS, []))
    monkeypatch.setattr(fetch_module, "record_snapshot", lambda *args, **kwargs: None)


def _refresh_button(at):
    return next(b for b in at.button if b.label == _REFRESH_LABEL)


def _blank_region_state(at, region="Hong Kong"):
    at.session_state[region] = None
    at.session_state[f"_fetched_{region}"] = None
    at.session_state[f"_stats_{region}"] = None


def test_app_runs_end_to_end_without_exception():
    at = AppTest.from_file(_MAIN, default_timeout=60)
    at.run()
    assert not at.exception
    assert at.sidebar


def test_region_switch_reruns_cleanly():
    at = AppTest.from_file(_MAIN, default_timeout=60)
    at.run()
    assert not at.exception
    segment = at.segmented_control[0]
    segment.set_value("Global").run()
    assert not at.exception


def test_chat_chip_flow():
    at = AppTest.from_file(_MAIN, default_timeout=60)
    at.run()
    assert not at.exception
    buttons = [b for b in at.button if b.key and b.key.startswith("chip-")]
    assert buttons
    target = next(b for b in buttons if b.key.endswith("top skills"))
    target.click().run()
    assert not at.exception


def test_first_load_does_not_auto_pull_when_no_state():
    at = AppTest.from_file(_MAIN, default_timeout=60)
    at.run()
    assert not at.exception
    _blank_region_state(at)
    at.run()
    assert at.session_state["Hong Kong"] is None


def test_refresh_button_gating_follows_fetch_age():
    at = AppTest.from_file(_MAIN, default_timeout=60)
    at.run()
    assert not at.exception

    at.session_state["region"] = "USA"
    at.session_state["_fetched_USA"] = time.time() - 10 * 86400
    at.run()
    assert not _refresh_button(at).disabled

    at.session_state["_fetched_USA"] = time.time()
    at.run()
    assert _refresh_button(at).disabled
