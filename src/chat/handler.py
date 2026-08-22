import re

import pandas as pd

from config import REGION_ALIASES, REGIONS, settings
from src.analysis.skills import SkillStat, compute_stats, get_matcher, lookup_skill, top_skills

_HELP_TEXT = (
    "I analyze the cached job listings for the selected region.\n\n"
    "**What you can ask:**\n"
    "- `top skills` / `hot tech stack` — ranked skill frequency + chart\n"
    "- a skill name like `python`, `react`, `kubernetes` — count, % and sample jobs\n"
    "- `how many jobs` — volume by source\n"
    "- `compare hk vs usa` — side-by-side counts **and %**\n"
    "- put `hk`, `usa` or `global` in any message to answer for that region"
)

_REGION_RE = re.compile(
    r"\b("
    + "|".join(re.escape(a) for a in sorted(REGION_ALIASES, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def respond(message: str, default_region: str, store) -> tuple[str, pd.DataFrame | None]:
    matcher = get_matcher()
    region = resolve_region(message) or default_region
    jobs = store.get(region)
    if not jobs:
        return (
            f"No jobs cached for **{region}** yet — click **Refresh jobs** in the sidebar first.",
            None,
        )
    lowered = message.lower()
    if re.search(r"\b(help|commands|what can you do)\b", lowered):
        return _HELP_TEXT, None
    if "compare" in lowered or " vs " in lowered:
        return _compare(store, message)
    if re.search(r"(how many|job count|count of jobs|jobs loaded|volume)", lowered):
        return _job_counts(jobs, region)
    if re.search(r"(top|hot|trend|popular|in demand|most wanted|required skill|skills?|tech stack)", lowered):
        return _top_skills(store, region)
    skill_name = matcher.resolve_query(message)
    if skill_name:
        return _skill_lookup(store, region, skill_name)
    guessed = _guess_skill(message)
    if guessed:
        return _skill_lookup(store, region, guessed)
    return (
        "I didn't catch that — type **help** to see supported questions "
        f"(currently answering for **{region}**).",
        None,
    )


_STOPWORDS = {
    "jobs", "job", "roles", "role", "positions", "position", "hiring", "skills", "skill",
    "tech", "stack", "trending", "trend", "hot", "top", "the", "and", "for", "with",
    "what", "which", "how", "much", "many", "often", "about", "need", "needs", "want",
    "using", "used", "use", "know", "tell", "show", "list", "give", "are", "was",
    "does", "did", "there", "here", "any", "some", "get", "into", "from",
}


def _guess_skill(message: str) -> str | None:
    lowered = message.lower()
    looks_like_skill_query = bool(
        re.search(r"\b(jobs?|hiring|roles?|positions?)\b", lowered)
    ) or lowered.rstrip().endswith("?")
    if not looks_like_skill_query:
        return None
    known_words = set(REGION_ALIASES) | {r.lower() for r in REGIONS} | _STOPWORDS
    tokens = re.findall(r"[a-z][a-z0-9+#.\-]{2,}", lowered)
    candidates = [t for t in tokens if t not in known_words]
    return max(candidates, key=len) if candidates else None


def resolve_region(message: str) -> str | None:
    match = _REGION_RE.search(message.lower())
    if not match:
        return None
    return REGION_ALIASES.get(match.group(1).lower())


def resolve_regions(message: str) -> list[str]:
    found: list[str] = []
    for match in _REGION_RE.finditer(message.lower()):
        region = REGION_ALIASES.get(match.group(1).lower())
        if region and region not in found:
            found.append(region)
    return found


def _stats_for(store, region: str) -> list[SkillStat]:
    key = f"_stats_{region}"
    if key not in store or store[key] is None:
        store[key] = compute_stats(store[region])
    return store[key]


def _stats_frame(stats: list[SkillStat]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "skill": [s.name for s in stats],
            "category": [s.category for s in stats],
            "jobs": [s.count for s in stats],
            "%": [s.pct for s in stats],
        }
    )


def _markdown_table(stats: list[SkillStat]) -> str:
    lines = ["| skill | category | jobs | % |", "|---|---|---|---|"]
    lines += [f"| {s.name} | {s.category} | {s.count} | {s.pct}% |" for s in stats]
    return "\n".join(lines)


def _top_skills(store, region: str) -> tuple[str, pd.DataFrame | None]:
    stats = top_skills(_stats_for(store, region))
    df = _stats_frame(stats)
    text = f"**Top skills in {region}** ({len(store[region])} jobs analyzed)\n\n" + _markdown_table(stats)
    return text, df


def _skill_lookup(store, region: str, skill_name: str) -> tuple[str, pd.DataFrame | None]:
    stat = lookup_skill(_stats_for(store, region), skill_name)
    if stat is None:
        return (
            f"**{skill_name}** doesn't appear in the {region} listings I have.",
            None,
        )
    samples = "\n".join(f"- {title}" for title in stat.sample_titles)
    total = len(store[region])
    text = (
        f"**{stat.name}** · `{stat.category}` appears in **{stat.count}/{total}** "
        f"{region} jobs (**{stat.pct}%**).\n\nSample roles:\n{samples}"
    )
    return text, None


def _job_counts(jobs: list, region: str) -> tuple[str, pd.DataFrame | None]:
    counts = pd.Series([job.source for job in jobs]).value_counts()
    lines = [f"**{region}**: {len(jobs)} jobs cached"]
    lines += [f"- {source}: {count}" for source, count in counts.items()]
    return "\n".join(lines), None


def _compare(store, message: str) -> tuple[str, pd.DataFrame | None]:
    requested = resolve_regions(message)
    missing = [r for r in requested if not store.get(r)]
    if len(requested) >= 2 and missing:
        return (
            f"No cached data for **{'**, **'.join(missing)}** — refresh those regions in the sidebar first.",
            None,
        )
    targets = [r for r in requested if store.get(r)] or [
        r for r in REGIONS if store.get(r)
    ]
    if len(targets) < 2:
        return (
            "I need at least two refreshed regions to compare — refresh another one in the sidebar.",
            None,
        )
    if not requested:
        targets = targets[:2]

    per_region: dict[str, dict[str, SkillStat]] = {
        region: {s.name: s for s in top_skills(_stats_for(store, region))}
        for region in targets
    }
    ranked: list[str] = []
    for region in targets:
        for name in per_region[region]:
            if name not in ranked:
                ranked.append(name)

    frame: dict[str, object] = {"skill": ranked}
    for region in targets:
        stats_map = per_region[region]
        total = len(store[region])
        frame[f"{region} jobs"] = [stats_map[name].count if name in stats_map else 0 for name in ranked]
        frame[f"{region} %"] = [
            round(stats_map[name].count / total * 100, 1) if name in stats_map else 0.0
            for name in ranked
        ]
    df = pd.DataFrame(frame)
    label = " vs ".join(targets)
    return f"**{label}** — job-listing mentions (count and % of regional pool):", df
