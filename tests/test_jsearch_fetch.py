"""Offline tests for the JSearch fetch loop's call budget.

Every test counts HTTP requests (via `fake_jsearch.calls`) to lock in the
"use as few JSearch calls as possible" behaviour:
  * sparse page 1  -> 1 call per keyword, page 2 never probed;
  * full page 1    -> page 2 only if it could plausibly add jobs;
  * pure-overlap   -> pagination stops as soon as a page adds nothing new;
  * job cap        -> later keywords are skipped once the pool is big enough.
"""

import src.sources.jsearch as jsearch
from tests.conftest import patch_jsearch_settings

_KEYWORDS = ["software engineer", "developer", "AI engineer", "analyst programmer"]


def _item(job_id: str, title: str = "Software Engineer") -> dict:
    return {"job_id": job_id, "job_title": title}


def _page(items: list[dict]) -> tuple[dict, None]:
    return {"data": items}, None


def _items(n: int, prefix: str) -> list[dict]:
    return [_item(f"{prefix}-{i}") for i in range(n)]


def test_fetch_without_key_makes_no_calls(monkeypatch, fake_jsearch):
    patch_jsearch_settings(monkeypatch, api_key="")
    jobs, error = jsearch.fetch(_KEYWORDS, "Hong Kong")
    assert jobs == [] and error is None
    assert fake_jsearch.calls == []


def test_sparse_page1_fetches_one_page_per_keyword(monkeypatch, fake_jsearch):
    patch_jsearch_settings(monkeypatch, jsearch_page_size=5)
    pages_by_query: dict[str, list[int]] = {}

    def responder(params):
        query = params["query"]
        pages_by_query.setdefault(query, []).append(int(params["page"]))
        return _page(_items(2, prefix=query.split()[0]))  # 2 < page size

    fake_jsearch.install(responder)
    jobs, error = jsearch.fetch(_KEYWORDS, "Hong Kong")
    assert error is None
    assert len(jobs) == len(_KEYWORDS) * 2
    # Exactly one request per keyword — page 2 is never probed.
    assert len(fake_jsearch.calls) == len(_KEYWORDS)
    assert all(pages == [1] for pages in pages_by_query.values())


def test_full_page1_paginates_once_then_sparse_page2_stops(monkeypatch, fake_jsearch):
    patch_jsearch_settings(monkeypatch, jsearch_page_size=5)
    pages_by_query: dict[str, list[int]] = {}

    def responder(params):
        query, page = params["query"], int(params["page"])
        pages_by_query.setdefault(query, []).append(page)
        if page == 1:
            return _page(_items(5, prefix=f"{query}-p1"))  # exactly full
        return _page(_items(1, prefix=f"{query}-p2"))  # sparse page 2

    fake_jsearch.install(responder)
    jobs, error = jsearch.fetch(_KEYWORDS[:1], "Hong Kong")
    assert error is None
    assert len(jobs) == 6  # 5 from page 1 + 1 from page 2
    query = _KEYWORDS[0] + " jobs in hong kong"
    assert pages_by_query[query] == [1, 2]
    assert len(fake_jsearch.calls) == 2


def test_overlapping_results_stop_pagination_per_keyword(monkeypatch, fake_jsearch):
    patch_jsearch_settings(monkeypatch, jsearch_page_size=5)
    pages_by_query: dict[str, list[int]] = {}

    def responder(params):
        query, page = params["query"], int(params["page"])
        pages_by_query.setdefault(query, []).append(page)
        return _page(_items(5, prefix="shared"))  # identical jobs every page

    fake_jsearch.install(responder)
    jobs, error = jsearch.fetch(_KEYWORDS, "USA")
    assert error is None
    assert len(jobs) == 5  # deduped across all keywords
    # Keywords after the first see only duplicates on page 1 -> one call each.
    assert len(fake_jsearch.calls) == 1 + len(_KEYWORDS)
    assert pages_by_query[_KEYWORDS[0]] == [1, 2]
    for query, pages in pages_by_query.items():
        if query != _KEYWORDS[0]:
            assert pages == [1], f"{query} should never paginate (pure overlap)"


def test_job_cap_stops_further_keywords(monkeypatch, fake_jsearch):
    patch_jsearch_settings(monkeypatch, jsearch_page_size=5, jsearch_max_jobs=5)
    called_queries: list[str] = []

    def responder(params):
        called_queries.append(params["query"])
        return _page(_items(5, prefix=params["query"]))

    fake_jsearch.install(responder)
    jobs, error = jsearch.fetch(_KEYWORDS, "USA")
    assert error is None
    assert len(jobs) == 5
    assert called_queries == [_KEYWORDS[0]]
    assert len(fake_jsearch.calls) == 1


def test_errors_aggregate_and_do_not_paginate(monkeypatch, fake_jsearch):
    patch_jsearch_settings(monkeypatch)

    def responder(params):
        return None, "HTTP 500"

    fake_jsearch.install(responder)
    jobs, error = jsearch.fetch(_KEYWORDS, "USA")
    assert jobs == []
    assert error == "HTTP 500 x4"
    assert len(fake_jsearch.calls) == len(_KEYWORDS)


def test_429_is_retried_once(monkeypatch, fake_jsearch):
    patch_jsearch_settings(monkeypatch)
    state = {"count": 0}

    def responder(params):
        state["count"] += 1
        if state["count"] == 1:
            return None, "HTTP 429"
        return _page([_item("recovered")])

    fake_jsearch.install(responder)
    jobs, error = jsearch.fetch(_KEYWORDS[:1], "USA")
    assert error is None
    assert [j.id for j in jobs] == ["jsearch:recovered"]
    assert len(fake_jsearch.calls) == 2


def test_empty_page_stops_keyword_without_paging(monkeypatch, fake_jsearch):
    patch_jsearch_settings(monkeypatch)

    def responder(params):
        return _page([])

    fake_jsearch.install(responder)
    jobs, error = jsearch.fetch(_KEYWORDS, "USA")
    assert jobs == [] and error is None
    assert len(fake_jsearch.calls) == len(_KEYWORDS)


def test_request_carries_api_key_header(monkeypatch, fake_jsearch):
    patch_jsearch_settings(monkeypatch, api_key="secret")

    def responder(params):
        return _page([_item("h1")])

    fake_jsearch.install(responder)
    jsearch.fetch(_KEYWORDS[:1], "USA")
    assert fake_jsearch.calls[0]["headers"] == {"x-api-key": "secret"}


def test_hk_query_gets_suffix_usa_does_not():
    assert jsearch._build_query("software engineer", "Hong Kong") == "software engineer jobs in hong kong"
    assert jsearch._build_query("AI engineer", "USA") == "AI engineer"
