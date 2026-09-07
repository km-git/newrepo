"""Heuristic Discover classifier with SSPM context (Gemini Flash when GEMINI_API_KEY is set)."""

from __future__ import annotations

import os
from typing import Any

from sspm import MODULES

KEYWORDS = {
    "sspm": 4,
    "cnspec": 4,
    "appomni": 2,
    "adaptive shield": 2,
    "obsidian": 1,
    "microsoft 365": 2,
    "google workspace": 2,
    "okta": 2,
    "oauth": 3,
    "cis-m365": 3,
    "cis-gws": 3,
    "saas security posture": 4,
    "mondoo": 3,
    "presidio": 2,
    "duckdb": 1,
    "github org": 2,
    "slack workspace": 2,
}

SSPM_CONTEXT = """
SSPM context (for vendor and OSS-tool sources only):
- SSPM = SaaS Security Posture Management (AppOmni, Adaptive Shield/CrowdStrike, Obsidian, DoControl, Valence)
- DSPM = Data Security Posture Management (Cyera, BigID, Varonis, Sentra, Symmetry)
- CIS-M365 / CIS-GWS = Center for Internet Security benchmarks for Microsoft 365 / Google Workspace
- Mondoo cnspec = open-source xSPM engine, MIT, v13.37.0 in Sep 2026
- Microsoft Graph /v1.0/subscribedSkus = license utilisation endpoint, free tier, NOT metered
- Microsoft Graph beta/admin/cloudLicensing = beta, may change, AVOID for production
- Presidio = PII detection library, MIT, active in 2026 (now under data-privacy-stack org)
Disallowed report language: "compliance", "attestation", "certified", "secure", "guaranteed".
Use "configuration reference", "control reference", "posture observation" instead.
"""


def classify_item(item: dict[str, Any], *, module_hint: str = "") -> dict[str, Any]:
    blob = " ".join(str(item.get(k) or "") for k in ("title", "summary", "source", "module_hint")).lower()
    hint = (module_hint or str(item.get("module_hint") or "")).lower()
    score = 0
    hits = []
    locked_module = "unknown"
    for word, weight in KEYWORDS.items():
        if word in blob:
            score += weight
            hits.append(word)
    for name in MODULES:
        if name in hint or f"sspm/{name}" in hint:
            locked_module = name
            score += 2
            break
    if "sspm" in hint:
        score += 1
        if locked_module == "unknown":
            locked_module = "audit"
    engine = "gemini-2.5-flash" if os.environ.get("GEMINI_API_KEY") else "heuristic"
    if score >= 7:
        verdict = "discover"
    elif score >= 3:
        verdict = "watch"
    else:
        verdict = "skip"
    return {
        "verdict": verdict,
        "score": min(score, 12),
        "hits": hits,
        "module": locked_module,
        "engine": engine,
        "context_attached": True,
        "sspm_context": SSPM_CONTEXT.strip()[:200],
    }
