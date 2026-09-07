"""DSPM resource gap audit — forums, GitHub tools, other tools, Python libs."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml

from dspm.loop.evaluate import evaluate_item

CATALOG_PATH = Path(__file__).with_name("catalog.yaml")
SOURCES_PATH = Path(__file__).with_name("sources.yaml")
ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = Path(os.environ.get("DSPM_GAP_AUDIT", "state/gap_audit.json"))

Impact = Literal["critical", "high", "medium", "low"]
Status = Literal["integrated", "partial", "missing", "candidate"]

_IMPACT_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def load_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    raw = yaml.safe_load((path or CATALOG_PATH).read_text(encoding="utf-8")) or {}
    items = raw.get("items") if isinstance(raw, dict) else raw
    return [dict(item) for item in (items or [])]


def _path_exists(rel: str | None) -> bool:
    if not rel:
        return False
    return (ROOT / rel).exists()


def _sources_text() -> str:
    if SOURCES_PATH.exists():
        return SOURCES_PATH.read_text(encoding="utf-8")
    return ""


def resolve_status(item: dict[str, Any], *, sources: str) -> Status:
    target = item.get("integrated_in")
    if target and _path_exists(str(target)):
        name = str(item.get("name") or item.get("id") or "")
        # Watching a feed is "integrated" for forums; for libs, path present is partial
        # unless the file is more than a watcher list.
        if item.get("category") == "forum":
            return "integrated"
        if str(target).endswith("column_heuristics.py"):
            return "partial"
        if str(target).endswith("recognizers.py") and "presidio" in name.lower():
            return "partial"
        if str(target).endswith("service.py") and item.get("id") in {"lib_duckdb", "lib_chromadb"}:
            return "partial"
        return "integrated"
    url = str(item.get("url") or "")
    if url and url in sources:
        return "partial"
    name = str(item.get("name") or "")
    if name and name.split("/")[-1] in sources:
        return "partial"
    return "missing"


def audit(*, catalog_path: Path | None = None) -> dict[str, Any]:
    sources = _sources_text()
    items: list[dict[str, Any]] = []
    for raw in load_catalog(catalog_path):
        entry = dict(raw)
        entry["status"] = resolve_status(raw, sources=sources)
        items.append(entry)

    gaps = [
        i for i in items if i["status"] in {"missing", "partial"} and i.get("impact") in {"critical", "high", "medium"}
    ]
    gaps.sort(key=lambda x: (_IMPACT_RANK.get(str(x.get("impact")), 9), str(x.get("category"))))

    by_category: dict[str, dict[str, int]] = {}
    for item in items:
        cat = str(item.get("category") or "other")
        by_category.setdefault(cat, {"integrated": 0, "partial": 0, "missing": 0, "candidate": 0})
        by_category[cat][item["status"]] = by_category[cat].get(item["status"], 0) + 1

    next_integrations = []
    for gap in gaps:
        if gap.get("category") == "forum":
            continue
        rubric = evaluate_item(
            {
                "title": gap.get("name"),
                "summary": gap.get("challenge"),
                "module_hint": gap.get("module"),
                "license": gap.get("license"),
                "category": gap.get("category"),
                "url": gap.get("url"),
            }
        )
        next_integrations.append(
            {
                "id": gap["id"],
                "name": gap.get("name"),
                "module": gap.get("module"),
                "url": gap.get("url"),
                "license": gap.get("license"),
                "impact": gap.get("impact"),
                "status": gap.get("status"),
                "first_commit": _first_commit(gap),
                "rubric": rubric,
            }
        )
        if len(next_integrations) >= 8:
            break

    return {
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "summary": {
            "total_watchlist": len(items),
            "gaps": len(gaps),
            "critical_gaps": sum(1 for g in gaps if g.get("impact") == "critical"),
            "high_gaps": sum(1 for g in gaps if g.get("impact") == "high"),
            "by_category": by_category,
        },
        "top_gaps": gaps[:15],
        "next_integrations": next_integrations,
        "challenge_questions": [str(g.get("challenge")) for g in gaps[:12]],
        "items": items,
    }


def save_audit(report: dict[str, Any], path: Path | None = None) -> Path:
    target = path or AUDIT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return target


def _first_commit(gap: dict[str, Any]) -> str:
    module = gap.get("module") or "dspm/audit"
    name = gap.get("name") or gap.get("id")
    cat = gap.get("category")
    if cat == "python_lib":
        return f"Add optional extra + adapter in {module} wrapping {name} (CLI or import with fallback)."
    if cat == "github_tool":
        return f"Add subprocess wrapper in {module} parsing {name} JSON; fixture in examples/."
    if cat == "other_tool":
        return f"Wire {name} into dspm-ci.yml (SHA-pin Actions; $0)."
    return f"Add {name} to dspm/loop/sources.yaml and classify() keywords."
