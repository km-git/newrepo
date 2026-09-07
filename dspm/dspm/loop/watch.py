"""Forum-watcher loop — Discover slot of the 5-stage improvement loop."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import yaml

STATE_DIR = Path(__file__).resolve().parents[2] / "state"
SOURCES_PATH = Path(__file__).resolve().parent / "sources.yaml"
SEEN_PATH = STATE_DIR / "seen.json"

DSPM_CONTEXT = """
DSPM context (for vendor and OSS-tool sources only):
- DSPM = Data Security Posture Management (Cyera, BigID, Varonis, Sentra)
- Presidio = Microsoft PII detection library, MIT (data-privacy-stack org)
- DuckDB = in-process analytical SQL
- CloudQuery = open-source cloud asset inventory
- Prowler = open-source CSPM, Apache-2.0
- Trivy = container/IaC scanner, v0.71.2 (avoid v0.69.4 — CVE-2026-33634)
- Steampipe = SQL over cloud APIs, AGPL-3.0 (CLI only)
- Cloud Custodian = policy-as-code, Apache-2.0
"""


def load_sources() -> list[dict]:
    if not SOURCES_PATH.exists():
        return []
    return yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")) or []


def load_seen() -> dict[str, str]:
    if SEEN_PATH.exists():
        return json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    return {}


def save_seen(seen: dict[str, str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(seen, indent=2), encoding="utf-8")


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def fetch_feed(url: str, max_items: int = 25) -> list[dict[str, Any]]:
    feed = feedparser.parse(url)
    items: list[dict[str, Any]] = []
    for entry in feed.entries[:max_items]:
        link = entry.get("link", entry.get("id", ""))
        items.append(
            {
                "title": entry.get("title", ""),
                "url": link,
                "summary": (entry.get("summary", "") or "")[:600],
                "published": entry.get("published", ""),
            }
        )
    return items


def classify_item(item: dict, module_hint: str = "") -> dict:
    """Rule-based classifier (Gemini Flash in production)."""
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    score = 5
    verdict = "watch"
    keywords = ["dspm", "presidio", "duckdb", "cloudquery", "prowler", "trivy", "cyera", "pii", "data security"]
    hits = sum(1 for k in keywords if k in text)
    score += min(hits * 2, 8)
    if score >= 7:
        verdict = "discover"
    elif score < 4:
        verdict = "skip"
    return {
        **item,
        "module_hint": module_hint,
        "score": score,
        "verdict": verdict,
        "classified_at": datetime.now(timezone.utc).isoformat(),
    }


def run_watch(mode: str = "all") -> dict:
    seen = load_seen()
    sources = load_sources()
    new_items: list[dict] = []
    for src in sources:
        host = (urlparse(src.get("url", "")).hostname or "").lower()
        if mode == "vendor" and (host == "reddit.com" or host.endswith(".reddit.com")):
            continue
        if mode == "community" and (host == "github.com" or host.endswith(".github.com")):
            continue
        try:
            items = fetch_feed(src["url"], src.get("max_items", 15))
        except Exception:
            continue  # skip feeds that fail to parse; watcher must not abort the loop
        for item in items:
            h = url_hash(item["url"])
            if h in seen:
                continue
            classified = classify_item(item, src.get("module_hint", ""))
            if classified["verdict"] != "skip":
                new_items.append(classified)
                seen[h] = datetime.now(timezone.utc).isoformat()
    save_seen(seen)
    return {"mode": mode, "new_items": new_items, "count": len(new_items)}
