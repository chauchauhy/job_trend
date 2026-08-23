"""Headless collector: pull job listings and append trend snapshots.

Usage:
    python scripts/update_history.py                 # all regions
    python scripts/update_history.py --regions hk,usa

Data directory resolves from JOB_TREND_DATA_DIR, else settings.paths.data.
"""

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import REGIONS, REGION_ALIASES, settings
from src.fetch import pull_and_record


def resolve_regions(raw: str | None) -> list[str]:
    if not raw:
        return list(REGIONS)
    known = {r.lower(): r for r in REGIONS}
    out: list[str] = []
    for token in raw.split(","):
        key = token.strip().lower()
        if not key:
            continue
        region = REGION_ALIASES.get(key) or known.get(key)
        if region is None:
            print(f"? unknown region '{token.strip()}' - skipped")
            continue
        if region not in out:
            out.append(region)
    return out


def _data_dir() -> Path:
    env = os.environ.get("JOB_TREND_DATA_DIR")
    return Path(env) if env else settings.paths.data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pull job feeds and append trend snapshots.")
    parser.add_argument("--regions", help="comma-separated regions (hk, usa, global). Default: all")
    args = parser.parse_args(argv)

    data_dir = _data_dir()
    failures = 0
    for region in resolve_regions(args.regions):
        try:
            jobs, _stats, warnings = pull_and_record(region, data_dir=data_dir)
        except Exception as exc:
            failures += 1
            print(f"[FAIL] {region}: {type(exc).__name__}: {exc}")
            continue
        notes = f" - {len(warnings)} note(s)" if warnings else ""
        print(f"[OK] {region}: {len(jobs)} listings{notes}")
        for warning in warnings:
            print(f"     - {warning}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
