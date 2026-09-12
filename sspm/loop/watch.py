"""Discover slot: extend forum-watcher; do not duplicate it."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from sspm.loop.classify import classify_item

ROOT = Path(__file__).resolve().parents[2]
FORUM_WATCH = ROOT / "forum-watcher" / "scripts" / "watch.py"
SOURCES = Path(__file__).with_name("sources.yaml")
STATE_DIR = Path("state")
SEEN = STATE_DIR / "seen.json"
QUEUE = STATE_DIR / "discover_queue.json"


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def load_sources() -> list[dict[str, Any]]:
    return list(yaml.safe_load(SOURCES.read_text(encoding="utf-8")) or [])


def load_seen(path: Path | None = None) -> dict[str, Any]:
    """Shared DSPM/SSPM seen file: `{"items": {sha: metadata}}`. Legacy list of hashes still loads."""
    target = path or SEEN
    if not target.exists():
        return {"items": {}}
    raw = json.loads(target.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return {"items": {h: {"source": "sspm"} for h in raw if isinstance(h, str)}}
    if isinstance(raw, dict):
        items = dict(raw.get("items") or {})
        state = {k: v for k, v in raw.items() if k != "items"}
        state["items"] = items
        return state
    return {"items": {}}


def save_seen(state: dict[str, Any], path: Path | None = None) -> None:
    target = path or SEEN
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(state)
    payload.setdefault("items", {})
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _import_forum_watcher():
    if not FORUM_WATCH.exists():
        return None
    sys.path.insert(0, str(FORUM_WATCH.parent))
    import watch as forum_watch  # type: ignore[import-not-found]

    return forum_watch


def watch(*, mode: str = "offline", fetch: bool = False) -> dict[str, Any]:
    """Run Discover. Live HTTP fetch is opt-in (`fetch=True`) so CI stays $0/offline."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    state = load_seen(SEEN)
    seen: set[str] = set((state.get("items") or {}).keys())
    forum = _import_forum_watcher() if fetch else None
    items = _live_fetch(forum, sources, seen) if forum and fetch else _offline_seed(sources, seen)
    classified = []
    for item in items:
        digest = url_hash(item["url"])
        seen.add(digest)
        item["url_sha256"] = digest
        item["classification"] = classify_item(item)
        classified.append(item)
        state.setdefault("items", {})[digest] = {
            "source": "sspm",
            "title": item.get("title"),
            "url": item.get("url"),
            "verdict": item["classification"].get("verdict"),
        }
    save_seen(state, SEEN)
    QUEUE.write_text(json.dumps(classified, indent=2, default=str) + "\n", encoding="utf-8")
    discoveries = [i for i in classified if i["classification"]["verdict"] == "discover"]
    return {
        "mode": mode,
        "fetched": bool(fetch and forum),
        "sources": len(sources),
        "new_items": len(classified),
        "discover": len(discoveries),
        "queue": str(QUEUE),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }


def _offline_seed(sources: list[dict[str, Any]], seen: set[str]) -> list[dict[str, Any]]:
    seed = {
        "source": "cnspec-releases",
        "title": "Mondoo cnspec 13.37.0 SSPM policy pack for Microsoft 365 and Google Workspace",
        "url": "https://github.com/mondoohq/cnspec/releases/tag/v13.37.0",
        "summary": "Open-source cnspec scan microsoft365 google-workspace github slack okta CIS-M365",
        "module_hint": "sspm/m365_discovery",
    }
    if url_hash(seed["url"]) in seen:
        return []
    _ = sources
    return [seed]


def _live_fetch(forum: Any, sources: list[dict[str, Any]], seen: set[str]) -> list[dict[str, Any]]:
    import httpx

    new_items: list[dict[str, Any]] = []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "sspm-watch/0.1"}) as client:
        for src in sources:
            try:
                fetched = forum.fetch_source(client, src)
            except Exception as exc:
                print(f"[skip] {src.get('name')}: {exc}")
                continue
            for item in fetched:
                digest = url_hash(item["url"])
                if digest in seen:
                    continue
                new_items.append(item)
    return new_items
