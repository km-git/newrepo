#!/usr/bin/env python3
"""First-Monday source-quality rollup → monthly/YYYY-MM.md."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DISCOVERIES = ROOT / "discoveries"
STATE = ROOT / "state"
ACCEPT = STATE / "accept-reject.jsonl"
TOOLS_PATH = ROOT / "free-test-tools.yaml"
OUT = ROOT / "monthly"

ITEM_RE = re.compile(
    r"^- \[[ xX]\] \*\*\[(?P<module>[^\]]+)\]\*\* \[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)\s*$"
)
META_RE = re.compile(r"^\s+(?P<source>.+?) · score (?P<score>\S+) · (?P<reason>.*)$")
MAJOR_RES = (
    re.compile(r"(?i)(?:^|[\s])v(\d+)\.0(?:\.|$|\s)"),
    re.compile(r"(?i)release\s+v?(\d+)\.0(?:\.|$|\s)"),
)


def load_tools() -> list[str]:
    if not TOOLS_PATH.exists():
        return []
    data = yaml.safe_load(TOOLS_PATH.read_text()) or {}
    tools = data.get("tools", data) if isinstance(data, dict) else data
    names = []
    for row in tools or []:
        if isinstance(row, dict) and row.get("name"):
            names.append(str(row["name"]))
    return names


def parse_discoveries(directory: Path) -> list[dict]:
    items: list[dict] = []
    if not directory.exists():
        return items
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("."):
            continue
        pending = None
        for line in path.read_text().splitlines():
            match = ITEM_RE.match(line)
            if match:
                pending = {
                    "file": path.name,
                    "month": path.name[:7] if path.name[:7].count("-") == 1 else path.stem[:7],
                    **match.groupdict(),
                    "source": "",
                    "score": "",
                    "checked": "[x]" in line.lower() or "[X]" in line,
                }
                continue
            if pending:
                meta = META_RE.match(line)
                if meta:
                    pending.update(meta.groupdict())
                    items.append(pending)
                    pending = None
                elif line.startswith("- "):
                    items.append(pending)
                    pending = None
        if pending:
            items.append(pending)
    return items


def load_decisions(path: Path) -> list[dict]:
    if not path.exists() or not path.read_text().strip():
        return []
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def accept_ratio(rows: list[dict]) -> dict[str, dict]:
    stats: dict[str, dict] = defaultdict(lambda: {"accept": 0, "reject": 0})
    for row in rows:
        source = str(row.get("source") or "unknown")
        decision = str(row.get("decision") or "").lower()
        if decision in {"accept", "reject"}:
            stats[source][decision] += 1
    out = {}
    for source, counts in stats.items():
        total = counts["accept"] + counts["reject"]
        ratio = counts["accept"] / total if total else 0.0
        out[source] = {**counts, "total": total, "ratio": ratio}
    return out


def community_shifts(current: dict[str, dict], previous: dict[str, dict]) -> list[dict]:
    flips = []
    for source, now in current.items():
        was = previous.get(source)
        if not was or was["total"] < 3 or now["total"] < 3:
            continue
        if was["ratio"] > 0.30 and now["ratio"] < 0.20:
            flips.append(
                {
                    "source": source,
                    "from": round(was["ratio"], 3),
                    "to": round(now["ratio"], 3),
                }
            )
    return flips


def split_by_month(rows: list[dict], year_month: str) -> tuple[list[dict], list[dict]]:
    current, previous = [], []
    prev_month = _prev_month(year_month)
    for row in rows:
        stamp = str(row.get("month") or row.get("date") or "")[:7]
        if stamp == year_month:
            current.append(row)
        elif stamp == prev_month:
            previous.append(row)
    return current, previous


def _prev_month(year_month: str) -> str:
    year, month = [int(x) for x in year_month.split("-")]
    month -= 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}-{month:02d}"


def major_version_crossings(items: list[dict]) -> list[dict]:
    found = []
    for item in items:
        source = item.get("source", "")
        title = item.get("title", "")
        if not any(tok in source.lower() for tok in ("releases", "sdk", "cvpysdk", "cohesity", "rubrik", "dell", "acronis", "commvault")):
            continue
        version = None
        for pat in MAJOR_RES:
            match = pat.search(title)
            if match:
                version = int(match.group(1))
                break
        if version is not None and version >= 2:
            found.append({"source": source, "title": title, "url": item.get("url", "")})
    return found


def new_tools(items: list[dict], known: list[str]) -> list[str]:
    known_l = {n.lower() for n in known}
    stop = {
        "backup", "backups", "release", "releases", "the", "and", "for", "with",
        "from", "how", "setup", "integration", "module", "python", "sdk",
    }
    hits = []
    for item in items:
        if "releases" not in item.get("source", "").lower() and "discussions" not in item.get("source", "").lower():
            continue
        title = item.get("title", "")
        for word in re.findall(r"[A-Z][A-Za-z0-9_.-]{2,}", title):
            if word.lower() in known_l or word.lower() in stop:
                continue
            if word.lower() in {h.lower() for h in hits}:
                continue
            if any(tok in word.lower() for tok in ("backup", "restic", "kopia", "weed", "velero", "wal-g", "ltfs", "seaweed", "borg")):
                hits.append(word)
    return hits


def render(year_month: str, items: list[dict], decisions: list[dict], tools: list[str]) -> str:
    cited = Counter(i.get("source") or "unknown" for i in items)
    top10 = cited.most_common(10)
    current_d, previous_d = split_by_month(decisions, year_month)
    # If jsonl rows have no month, treat the whole file as current.
    if not current_d and not previous_d and decisions:
        current_d = decisions
    ratios = accept_ratio(current_d)
    prev_ratios = accept_ratio(previous_d)
    flips = community_shifts(ratios, prev_ratios)
    majors = major_version_crossings(items)
    emerging = new_tools(items, tools)

    lines = [
        f"# Monthly rollup — {year_month}",
        "",
        f"Discover items parsed: **{len(items)}**. Accept/reject rows: **{len(decisions)}**.",
        "",
        "## Top 10 most-cited sources",
        "",
    ]
    if not top10:
        lines.append("_No discoveries this month._")
        lines.append("")
    else:
        for i, (source, count) in enumerate(top10, 1):
            lines.append(f"{i}. `{source}` — {count}")
        lines.append("")

    lines += ["## Accept/reject ratio per source", ""]
    if not ratios:
        lines.append("_No `state/accept-reject.jsonl` decisions yet. Check boxes in weekly PRs, then log `{\"source\",\"url\",\"decision\":\"accept|reject\",\"month\":\"YYYY-MM\"}`._")
        lines.append("")
    else:
        lines.append("| Source | Accept | Reject | Ratio |")
        lines.append("|--------|--------|--------|-------|")
        for source, row in sorted(ratios.items(), key=lambda kv: kv[1]["ratio"]):
            lines.append(f"| `{source}` | {row['accept']} | {row['reject']} | {row['ratio']:.0%} |")
        lines.append("")

    lines += ["## Community-shift flips (accept >30% → <20%)", ""]
    if not flips:
        lines.append("_None._")
        lines.append("")
    else:
        for flip in flips:
            lines.append(f"- `{flip['source']}` {flip['from']:.0%} → {flip['to']:.0%}")
        lines.append("")

    lines += ["## Vendor major-version crossings", ""]
    if not majors:
        lines.append("_None detected in discovery titles._")
        lines.append("")
    else:
        for row in majors:
            lines.append(f"- {row['source']}: [{row['title']}]({row['url']})")
        lines.append("")

    lines += ["## New free tools vs `free-test-tools.yaml`", ""]
    if not emerging:
        lines.append("_None._")
        lines.append("")
    else:
        for name in emerging:
            lines.append(f"- `{name}`")
        lines.append("")

    lines += [
        "## Notes",
        "",
        "Classification stays on Gemini Flash-Lite (15 RPM / 1,000 RPD). No Sonnet/Opus.",
        "mhvtl validation is self-hosted only.",
        "",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monthly forum-watcher rollup")
    parser.add_argument(
        "--month",
        default=datetime.now(timezone.utc).strftime("%Y-%m"),
        help="YYYY-MM",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    items = parse_discoveries(DISCOVERIES)
    # Keep items whose filename month matches, else include all (first run).
    month_items = [i for i in items if i.get("file", "").startswith(args.month)] or items
    md = render(args.month, month_items, load_decisions(ACCEPT), load_tools())
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.month}.md"
    path.write_text(md)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
