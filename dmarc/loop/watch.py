"""Watcher payload: reuse forum-watcher, add DMARC classify context."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

WATCH_PATH = Path(__file__).resolve().parents[2] / "forum-watcher" / "scripts" / "watch.py"

DMARC_CONTEXT = """
DMARC / Deliverability context (for vendor and OSS-tool sources only):
- DMARC = Domain-based Message Authentication, Reporting & Conformance (RFC 7489)
- SPF = Sender Policy Framework (RFC 7208), 10-DNS-lookup limit
- DKIM = DomainKeys Identified Mail (RFC 6376), RSA key ≥ 1024 bits recommended
- MTA-STS = SMTP MTA Strict Transport Security (RFC 8461)
- TLS-RPT = TLS Reporting (RFC 8460)
- BIMI = Brand Indicators for Message Identification (draft-ietf-bimi)
- parsedmarc = open-source DMARC report parser + visualizer, MIT, v8.6.4 in Sep 2026
- dnspython = DNS toolkit for Python, BSD
- Inbox placement = heuristic test, no open-source standard; commercial vendors: Valimail, dmarcian, OnDMARC, Postmark
- Valimail acquired by DigiCert in Sep 2025 (or Proofpoint in 2024 — sources disagree; both reported)
- Postmark DMARC = free tier, unlimited volume, top 10 sources only
- dmarcian = free personal plan for 1,250 messages/month
- Cloudflare DMARC Management = free for Cloudflare DNS customers (GA 2026-06-16)

Module hint bias: {module_hint}
If module_hint contains "dmarc" or one of the 9 module names, lock module-fit to the matching module.

Disallowed report language: "compliance", "attestation", "certified", "secure", "guaranteed". Use "deliverability observation", "authentication reference", "brand-protection observation" instead.
"""

DMARC_MODULES = (
    "audit",
    "dns_check",
    "spf_parser",
    "dkim_check",
    "dmarc_ingest",
    "aggregate_report",
    "forensic_report",
    "inbox_placement",
    "report_writer",
)


def load_watch():
    spec = importlib.util.spec_from_file_location("forum_watch", WATCH_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {WATCH_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def dmarc_prompt(module_hint: str) -> str:
    return DMARC_CONTEXT.format(module_hint=module_hint or "none")


def heuristic_classify(item: dict) -> dict:
    blob = f"{item.get('title', '')} {item.get('summary', '')} {item.get('module_hint', '')}".lower()
    module = "unknown"
    fit = 0
    for name in DMARC_MODULES:
        token = name.replace("_", " ")
        if name in blob or token in blob or name.replace("_", "-") in blob:
            module = name
            fit = 3
            break
    if "dmarc" in blob or "spf" in blob or "dkim" in blob:
        module = module if module != "unknown" else "dmarc_ingest"
        fit = max(fit, 3)
    action = 3 if any(k in blob for k in ("github.com", "pip install", "how to", "parsedmarc")) else 1
    trust = 2 if "releases" in str(item.get("source", "")).lower() else 1
    score = min(12, fit + action + 2 + trust)
    if score >= 7:
        verdict = "discover"
    elif score >= 5:
        verdict = "watch"
    else:
        verdict = "skip"
    return {"module": module, "score": score, "verdict": verdict, "reason": "dmarc heuristic"}
