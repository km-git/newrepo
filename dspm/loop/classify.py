"""Heuristic Discover classifier (Gemini Flash when GEMINI_API_KEY is set)."""

from __future__ import annotations

import os
from typing import Any

KEYWORDS = {
    "dspm": 3,
    "presidio": 3,
    "cyera": 2,
    "bigid": 2,
    "prowler": 2,
    "trivy": 2,
    "duckdb": 2,
    "cloudquery": 2,
    "steampipe": 2,
    "custodian": 2,
    "pii": 2,
    "gdpr": 1,
    "hipaa": 1,
    "shadow data": 3,
    "data security posture": 4,
}


def classify_item(item: dict[str, Any], *, dspm_context: str = "") -> dict[str, Any]:
    blob = " ".join(str(item.get(k) or "") for k in ("title", "summary", "source", "module_hint")).lower()
    score = 0
    hits = []
    for word, weight in KEYWORDS.items():
        if word in blob:
            score += weight
            hits.append(word)
    if "dspm" in str(item.get("module_hint") or "").lower():
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
        "context_attached": bool(dspm_context.strip()),
    }
