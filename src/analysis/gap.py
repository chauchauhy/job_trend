import json
from pathlib import Path

from config import settings
from src.analysis.skills import SkillMatcher

_FILE = "my_skills.json"


def normalize_skills(tokens: list[str], matcher: SkillMatcher) -> list[str]:
    canonical: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        name = token.strip()
        if not name:
            continue
        resolved = matcher.resolve_query(name)
        if not resolved or resolved in seen:
            continue
        seen.add(resolved)
        canonical.append(resolved)
    return canonical


def _path(data_dir: Path | None) -> Path:
    base = data_dir if data_dir is not None else settings.paths.data
    return base / _FILE


def load_own_skills(*, data_dir: Path | None = None) -> list[str]:
    path = _path(data_dir)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding=settings.data.encoding))
        if isinstance(raw, list):
            return [str(item) for item in raw]
        return []
    except (OSError, ValueError, TypeError):
        return []


def save_own_skills(skills: list[str], *, data_dir: Path | None = None) -> None:
    path = _path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(skills, ensure_ascii=False), encoding=settings.data.encoding)
