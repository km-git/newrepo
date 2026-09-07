"""SSPM forum watcher — extends tape-to-cloud pattern."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "state"
STATE = STATE_DIR / "seen.json"
SOURCES = Path(__file__).resolve().parent / "sources.yaml"
OUT = ROOT / "discoveries" / "sspm"

SSPM_CONTEXT = """
SSPM context (for vendor and OSS-tool sources only):
- SSPM = SaaS Security Posture Management (AppOmni, Adaptive Shield/CrowdStrike, Obsidian, DoControl, Valence)
- DSPM = Data Security Posture Management (Cyera, BigID, Varonis, Sentra, Symmetry)
- CIS-M365 / CIS-GWS = Center for Internet Security benchmarks for Microsoft 365 / Google Workspace
- Mondoo cnspec = open-source xSPM engine, MIT, v13.37.0
- Presidio = PII detection library, MIT, active in 2026 (data-privacy-stack org)

Disallowed report language: use "configuration reference", "control reference", "posture observation".
"""


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def load_seen() -> set[str]:
    if not STATE.exists():
        return set()
    data = json.loads(STATE.read_text(encoding="utf-8"))
    return set(data) if isinstance(data, list) else set()


def save_seen(seen: set[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(sorted(seen), indent=2), encoding="utf-8")


def load_sources() -> list[dict[str, Any]]:
    if not SOURCES.exists():
        return []
    data = yaml.safe_load(SOURCES.read_text(encoding="utf-8")) or {}
    return data.get("sources", [])


def classify(title: str, summary: str, module_hint: str = "sspm") -> dict[str, Any]:
    blob = f"{title} {summary}".lower()
    score = 5
    module = "sspm/audit"
    if "cnspec" in blob or "mondoo" in blob:
        score = 9
        module = "sspm/m365_discovery"
    elif "m365" in blob or "microsoft 365" in blob:
        score = 8
        module = "sspm/m365_discovery"
    elif "google workspace" in blob or "gws" in blob:
        score = 8
        module = "sspm/google_workspace_discovery"
    elif "github" in blob:
        score = 7
        module = "sspm/github_discovery"
    elif "slack" in blob:
        score = 7
        module = "sspm/slack_discovery"
    elif "okta" in blob:
        score = 7
        module = "sspm/okta_discovery"
    elif "oauth" in blob:
        score = 8
        module = "sspm/oauth_grants"
    if module_hint and module_hint in blob:
        score = min(10, score + 1)
    return {
        "score": score,
        "module": module,
        "context": SSPM_CONTEXT.strip(),
        "classifier": os.environ.get("GEMINI_MODEL", "heuristic"),
    }


def watch(*, fetch: bool = False) -> dict[str, Any]:
    seen = load_seen()
    sources = load_sources()
    discoveries: list[dict[str, Any]] = []
    for src in sources:
        url = src.get("url", "")
        if not url:
            continue
        h = url_hash(url)
        if h in seen:
            continue
        title = src.get("name", url)
        summary = src.get("description", "")
        result = classify(title, summary, src.get("module_hint", "sspm"))
        if result["score"] >= 7:
            discoveries.append(
                {
                    "source": src.get("name"),
                    "url": url,
                    "title": title,
                    "score": result["score"],
                    "module": result["module"],
                    "discovered_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                }
            )
            seen.add(h)
    save_seen(seen)
    if discoveries:
        OUT.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d")
        out_file = OUT / f"discoveries_{stamp}.md"
        lines = ["# SSPM Discoveries\n"]
        for d in discoveries:
            lines.append(f"- [{d['title']}]({d['url']}) — score {d['score']}, module `{d['module']}`\n")
        out_file.write_text("\n".join(lines), encoding="utf-8")
    return {"discoveries": discoveries, "seen_count": len(seen), "fetch": fetch}
