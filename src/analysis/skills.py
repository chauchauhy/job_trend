import json
import re
from dataclasses import dataclass

from config import settings
from src.models import Job

_ALIASES_KEY = "aliases"
_LOOKBEHIND = r"(?<![A-Za-z0-9+#])"
_LOOKAHEAD = r"(?![A-Za-z0-9+#])"

_MATCHER: "SkillMatcher | None" = None


@dataclass(frozen=True, slots=True)
class SkillStat:
    name: str
    category: str
    count: int
    pct: float
    sample_titles: tuple[str, ...]
    score: int = 0


def load_lexicon() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    path = settings.paths.config / "skills.json"
    with open(path, encoding=settings.data.encoding) as fh:
        raw: dict = json.load(fh)
    categories: dict[str, list[str]] = {
        cat: list(skills) for cat, skills in raw.get("categories", {}).items()
    }
    aliases: dict[str, list[str]] = {
        k.lower(): [a.lower() for a in v] for k, v in raw.get(_ALIASES_KEY, {}).items()
    }
    return categories, aliases


def get_matcher() -> "SkillMatcher":
    global _MATCHER
    if _MATCHER is None:
        _MATCHER = SkillMatcher()
    return _MATCHER


class SkillMatcher:
    def __init__(self) -> None:
        self.categories, self.aliases = load_lexicon()
        self.patterns: dict[str, re.Pattern[str]] = {}
        self.category_of: dict[str, str] = {}
        self.alias_of: dict[str, tuple[str, ...]] = {}
        for cat, skills in self.categories.items():
            for name in skills:
                alts = sorted(
                    {name, *self.aliases.get(name.lower(), [])},
                    key=len,
                    reverse=True,
                )
                body = "|".join(re.escape(a) for a in alts)
                self.patterns[name] = re.compile(f"{_LOOKBEHIND}(?:{body}){_LOOKAHEAD}", re.IGNORECASE)
                self.category_of[name] = cat
                self.alias_of[name] = tuple(self.aliases.get(name.lower(), []))

    def find_in_text(self, text: str) -> set[str]:
        return {name for name, pattern in self.patterns.items() if pattern.search(text)}

    def resolve_query(self, query: str) -> str | None:
        hits = self.find_in_text(query)
        if not hits:
            lowered = query.strip().lower()
            if lowered and len(lowered) >= 3:
                for name in self.patterns:
                    if lowered in name.lower() or name.lower() == lowered:
                        hits.add(name)
        if not hits:
            return None
        return max(hits, key=len)


def compute_stats(jobs: list[Job], matcher: SkillMatcher | None = None) -> list[SkillStat]:
    matcher = matcher or get_matcher()
    mentions: dict[str, set[str]] = {name: set() for name in matcher.patterns}
    title_mentions: dict[str, set[str]] = {name: set() for name in matcher.patterns}
    titles: dict[str, str] = {}
    for job in jobs:
        title_hits = matcher.find_in_text(job.title)
        full_text = " ".join((job.title, job.description, *job.tags))
        for name in matcher.find_in_text(full_text):
            mentions[name].add(job.id)
            titles[job.id] = job.title
            if name in title_hits:
                title_mentions[name].add(job.id)
    total = len(jobs)
    stats: list[SkillStat] = []
    for name, ids in mentions.items():
        count = len(ids)
        if count == 0:
            continue
        samples: list[str] = []
        for job_id in ids:
            title = titles.get(job_id)
            if title and title not in samples:
                samples.append(title)
            if len(samples) >= 3:
                break
        stats.append(
            SkillStat(
                name=name,
                category=matcher.category_of[name],
                count=count,
                pct=round(count / total * 100, 1) if total else 0.0,
                sample_titles=tuple(samples),
                score=count + len(title_mentions[name]),
            )
        )
    stats.sort(key=lambda s: (-s.score, -s.count, s.name.lower()))
    return stats


def top_skills(stats: list[SkillStat], top_n: int | None = None, category: str | None = None) -> list[SkillStat]:
    limit = top_n if top_n is not None else settings.display.top_n
    pool = [s for s in stats if category is None or s.category == category]
    return pool[:limit]


def lookup_skill(stats: list[SkillStat], name: str) -> SkillStat | None:
    target = name.lower()
    for stat in stats:
        if stat.name.lower() == target:
            return stat
    return next((s for s in stats if target in s.name.lower()), None)
