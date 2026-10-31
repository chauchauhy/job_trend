"""Shared offline fixtures — no test ever hits a live API."""

import time
from types import SimpleNamespace

import pytest


@pytest.fixture
def fake_jsearch(monkeypatch):
    """Neutralize JSearch HTTP + sleep and record every request.

    Install a canned responder via `fake_jsearch.install(responder)` where
    `responder(params)` returns what base.get_json would produce: `(payload, error)`.
    `fake_jsearch.calls` records each request's URL/params/headers so tests can
    assert exactly how many API calls a given scenario makes.
    """
    import src.sources.jsearch as jsearch_mod

    calls: list[dict] = []
    state = {"responder": None}

    def install(responder):
        state["responder"] = responder

    def fake_get_json(url, params=None, headers=None):
        calls.append({"url": url, "params": params, "headers": headers})
        responder = state["responder"]
        if responder is None:
            return {"data": []}, None
        return responder(params)

    monkeypatch.setattr(jsearch_mod, "get_json", fake_get_json)
    monkeypatch.setattr(time, "sleep", lambda _secs: None)
    return SimpleNamespace(calls=calls, install=install)


def patch_jsearch_settings(monkeypatch, api_key: str = "test-key", **fetch_overrides):
    """Point the jsearch module at Settings with a valid API key.

    Keep shipping config by default; pass overrides such as
    `jsearch_page_size=3, jsearch_max_jobs=6` to shape pagination tests, or
    `api_key=""` to simulate a keyless deployment.
    """
    from dataclasses import replace

    from config import ApiConfig, Settings

    import src.sources.jsearch as jsearch_mod

    base = jsearch_mod.settings
    fetch = replace(base.fetch, **fetch_overrides) if fetch_overrides else base.fetch
    patched = Settings(api=ApiConfig(jsearch_api_key=api_key), fetch=fetch)
    monkeypatch.setattr(jsearch_mod, "settings", patched)
    return patched
