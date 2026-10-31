import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True, slots=True)
class Paths:
    root: Path = ROOT_DIR
    src: Path = field(default_factory=lambda: ROOT_DIR / "src")
    res: Path = field(default_factory=lambda: ROOT_DIR / "res")
    data: Path = field(default_factory=lambda: ROOT_DIR / "res" / "data")
    images: Path = field(default_factory=lambda: ROOT_DIR / "res" / "images")
    config: Path = field(default_factory=lambda: ROOT_DIR / "res" / "config")


@dataclass(frozen=True, slots=True)
class AppConfig:
    title: str = "Job Trend"
    version: str = "Beta"
    layout: str = "wide"
    page_icon: str | None = None


@dataclass(frozen=True, slots=True)
class DataConfig:
    encoding: str = "utf-8"
    csv_separator: str = ","


@dataclass(frozen=True, slots=True)
class DisplayConfig:
    date_format: str = "%Y-%m-%d"
    top_n: int = 10


@dataclass(frozen=True, slots=True)
class ApiConfig:
    jsearch_api_key: str = field(default_factory=lambda: os.getenv("JSEARCH_API_KEY", ""))
    jobicy_url: str = "https://jobicy.com/api/v2/remote-jobs"
    remotive_url: str = "https://remotive.com/api/remote-jobs"
    remoteok_url: str = "https://remoteok.com/api"
    jsearch_base_url: str = "https://api.openwebninja.com/jsearch"
    user_agent: str = "job-trend-demo/1.0 (streamlit; contact: local)"
    timeout_s: float = 20.0


@dataclass(frozen=True, slots=True)
class FetchConfig:
    max_jobs_per_region: int = 150
    jsearch_max_pages_per_keyword: int = 2
    jsearch_page_size: int = 10
    jsearch_max_jobs: int = 150
    jsearch_delay_s: float = 1.1
    retry_backoff_s: float = 2.5
    jobicy_count: int = 50
    request_delay_s: float = 0.4
    cache_ttl_hours: int = 6
    refresh_unlock_days: int = 7


REGIONS: dict[str, str] = {
    "Hong Kong": "Hong Kong",
    "USA": "United States",
    "Global": "",
}

REMOTE_SOURCES_REGIONS: tuple[str, ...] = ("USA", "Global")

JSEARCH_REGIONS: tuple[str, ...] = ("Hong Kong", "USA")

JSEARCH_COUNTRY: dict[str, str] = {
    "USA": "us",
}

JSEARCH_QUERY_SUFFIX: dict[str, str] = {
    "Hong Kong": " jobs in hong kong",
}

REGION_ALIASES: dict[str, str] = {
    "hk": "Hong Kong",
    "hong kong": "Hong Kong",
    "usa": "USA",
    "us": "USA",
    "united states": "USA",
    "america": "USA",
    "global": "Global",
    "worldwide": "Global",
    "world": "Global",
}

FX_RATES: dict[str, float] = {
    "HKD": 7.80,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.36,
    "AUD": 1.52,
}

REGION_DEFAULT_CURRENCY: dict[str, str] = {
    "Hong Kong": "HKD",
    "USA": "USD",
    "Global": "USD",
}


@dataclass(frozen=True, slots=True)
class Settings:
    paths: Paths = field(default_factory=Paths)
    app: AppConfig = field(default_factory=AppConfig)
    data: DataConfig = field(default_factory=DataConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    fetch: FetchConfig = field(default_factory=FetchConfig)


settings = Settings()
