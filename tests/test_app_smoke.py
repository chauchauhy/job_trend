from pathlib import Path

from streamlit.testing.v1 import AppTest

_MAIN = str(Path(__file__).resolve().parents[1] / "main.py")


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
