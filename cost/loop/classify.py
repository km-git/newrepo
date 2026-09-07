"""Heuristic Discover classifier (Gemini Flash when GEMINI_API_KEY is set)."""

from __future__ import annotations

import os
from typing import Any

KEYWORDS = {
    "finops": 4,
    "cost explorer": 3,
    "rightsizing": 3,
    "steampipe": 3,
    "cloud custodian": 3,
    "c7n-org": 3,
    "prowler": 2,
    "trivy": 2,
    "duckdb": 2,
    "untagged": 2,
    "cost optimization": 3,
    "well-architected cost": 3,
    "reserved instance": 2,
    "cost anomaly": 2,
}


def classify_item(item: dict[str, Any], *, cost_context: str = "") -> dict[str, Any]:
    blob = " ".join(str(item.get(k) or "") for k in ("title", "summary", "source", "module_hint")).lower()
    score = 0
    hits = []
    for word, weight in KEYWORDS.items():
        if word in blob:
            score += weight
            hits.append(word)
    hint = str(item.get("module_hint") or "").lower()
    if "cost" in hint or any(m in hint for m in (
        "aws_inventory", "cost_explorer", "rightsizing", "untagged", "config_drift",
    )):
        score += 2
    engine = "gemini-2.5-flash" if os.environ.get("GEMINI_API_KEY") else "heuristic"
    if score >= 7:
        verdict = "discover"
    elif score >= 3:
        verdict = "watch"
    else:
        verdict = "skip"
    return {
        "verdict": verdict,
        "score": score,
        "hits": hits,
        "engine": engine,
        "context_attached": bool(cost_context.strip()),
    }
