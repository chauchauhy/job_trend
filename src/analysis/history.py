import json
from pathlib import Path

from config import settings
from src.analysis.skills import SkillStat

MAX_SNAPSHOTS = 180


def _path(region: str, data_dir: Path | None) -> Path:
    base = data_dir if data_dir is not None else settings.paths.data
    slug = region.lower().replace(" ", "_")
    return base / f"history_{slug}.json"


def load_history(region: str, *, data_dir: Path | None = None) -> list[dict]:
    path = _path(region, data_dir)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding=settings.data.encoding))
        snapshots = raw["snapshots"]
        if isinstance(snapshots, list):
            return [snap for snap in snapshots if isinstance(snap, dict)]
        return []
    except (OSError, ValueError, KeyError, TypeError):
        return []


def record_snapshot(
    region: str,
    ts: float,
    total: int,
    stats: list[SkillStat],
    *,
    data_dir: Path | None = None,
    salary: dict | None = None,
) -> None:
    snapshots = load_history(region, data_dir=data_dir)
    snapshot = {
        "ts": float(ts),
        "total": int(total),
        "skills": {stat.name: int(stat.count) for stat in stats},
    }
    if salary is not None:
        snapshot["salary"] = salary
    snapshots.append(snapshot)
    path = _path(region, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"snapshots": snapshots[-MAX_SNAPSHOTS:]}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding=settings.data.encoding)
