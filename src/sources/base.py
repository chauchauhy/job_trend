import re
from typing import Any

import requests

from config import settings

_TAG_BLOCK_RE = re.compile(r"(?is)<(script|style).*?>.*?</\1>")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_USA_RE = re.compile(r"\b(?:usa|united states|u\.s\.a?\.?)\b", re.IGNORECASE)


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = _TAG_BLOCK_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def usa_region(text: str | None) -> str:
    if text and _USA_RE.search(text):
        return "USA"
    return "Global"


def http_headers() -> dict[str, str]:
    return {"User-Agent": settings.api.user_agent, "Accept": "application/json"}


def get_json(url: str, params: dict | None = None, headers: dict | None = None) -> tuple[Any, str | None]:
    return _request("GET", url, params=params, extra_headers=headers)


def post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[Any, str | None]:
    return _request("POST", url, json_payload=payload, extra_headers=headers)


def _request(
    method: str,
    url: str,
    params: dict | None = None,
    json_payload: dict | None = None,
    extra_headers: dict | None = None,
) -> tuple[Any, str | None]:
    request_headers = {**http_headers(), **(extra_headers or {})}
    try:
        resp = requests.request(
            method,
            url,
            params=params,
            json=json_payload,
            headers=request_headers,
            timeout=settings.api.timeout_s,
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        return None, f"HTTP {status}"
    except requests.ConnectionError:
        return None, "connection error"
    except requests.Timeout:
        return None, "timeout"
    except ValueError:
        return None, "invalid JSON"
    except requests.RequestException as exc:
        return None, type(exc).__name__
