"""Forum watcher loop — extends forum-watcher with DMARC vendor context."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "state"
STATE = STATE_DIR / "seen.json"
SOURCES = ROOT / "sources.yaml"
DISCOVERIES = ROOT / "discoveries"

DMARC_MODULES = (
    "audit, dns_check, spf_parser, dkim_check, dmarc_ingest, aggregate_report, "
    "forensic_report, inbox_placement, report_writer"
)

DMARC_CONTEXT = """
DMARC / Deliverability context (for vendor and OSS-tool sources only):
- DMARC = Domain-based Message Authentication, Reporting & Conformance (RFC 7489)
- SPF = Sender Policy Framework (RFC 7208), 10-DNS-lookup limit
- DKIM = DomainKeys Identified Mail (RFC 6376), RSA key ≥ 1024 bits recommended
- parsedmarc = open-source DMARC report parser + visualizer, MIT
- dnspython = DNS toolkit for Python, BSD
- Inbox placement = heuristic test; no open-source standard
Disallowed report language: compliance, attestation, certified, secure, guaranteed.
Use deliverability observation, authentication reference, brand-protection observation instead.
"""


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def classify(item: dict) -> dict:
    blob = f"{item.get('title','')} {item.get('summary','')}".lower()
    module = "unknown"
    for name in DMARC_MODULES.split(","):
        token = name.strip()
        if token.replace("_", " ") in blob or token in blob:
            module = token
            break
    hint = str(item.get("module_hint", ""))
    if module == "unknown" and hint:
        module = hint.split(",")[0].strip()
    score = 8 if any(k in blob for k in ("parsedmarc", "dmarc", "spf", "dkim", "dnspython")) else 4
    verdict = "discover" if score >= 7 else "watch" if score >= 5 else "skip"
    return {"module": module, "score": score, "verdict": verdict, "reason": "dmarc heuristic"}


def run_watch() -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    DISCOVERIES.mkdir(parents=True, exist_ok=True)
    seen = set(json.loads(STATE.read_text())) if STATE.exists() else set()
    sources = yaml.safe_load(SOURCES.read_text()) if SOURCES.exists() else []
    new_items: list[dict] = []

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for src in sources:
            try:
                resp = client.get(src["url"])
                resp.raise_for_status()
                import feedparser

                feed = feedparser.parse(resp.text)
                for entry in feed.entries[: src.get("max_items", 10)]:
                    url = entry.get("link") or entry.get("id")
                    if not url:
                        continue
                    digest = url_hash(url)
                    if digest in seen:
                        continue
                    seen.add(digest)
                    new_items.append(
                        {
                            "title": entry.get("title", ""),
                            "url": url,
                            "summary": (entry.get("summary") or "")[:400],
                            "module_hint": src.get("module_hint", ""),
                        }
                    )
            except Exception as exc:
                print(f"skip {src.get('name')}: {exc}", file=sys.stderr)

    classified = [{**item, "classification": classify(item)} for item in new_items]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if classified:
        lines = [f"# DMARC discoveries — {today}", "", DMARC_CONTEXT.strip(), ""]
        for item in classified:
            c = item["classification"]
            lines.append(f"- [{c['module']}] {item['title']} ({c['verdict']}) — {item['url']}")
        (DISCOVERIES / f"{today}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    STATE.write_text(json.dumps(sorted(seen), indent=2) + "\n", encoding="utf-8")
    discover = sum(1 for i in classified if i["classification"]["verdict"] == "discover")
    return {"new": len(new_items), "discover": discover}


def monthly_rollup() -> Path:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    out_dir = ROOT / "monthly"
    out_dir.mkdir(parents=True, exist_ok=True)
    from dmarc.db import count_rows, fetch_all

    dmarc = fetch_all("findings_dmarc", limit=1000)
    inbox = fetch_all("findings_inbox", limit=100)
    pass_rows = sum(1 for r in dmarc if r.get("dkim_result") == "pass" and r.get("spf_result") == "pass")
    inbox_inbox = sum(1 for r in inbox if r.get("placement") == "inbox")
    trend = out_dir / "deliverability-trend.md"
    trend.write_text(
        f"# Deliverability trend — {month}\n\n"
        f"- DMARC aggregate rows: {len(dmarc)} (pass-like: {pass_rows})\n"
        f"- Inbox placement inbox hits: {inbox_inbox}/{len(inbox) or 1}\n"
        f"- DNS rows: {count_rows('findings_dns')}\n",
        encoding="utf-8",
    )
    rollup = out_dir / f"{month}.md"
    rollup.write_text(f"# Monthly rollup {month}\n\nSee deliverability-trend.md for KPIs.\n", encoding="utf-8")
    return trend
