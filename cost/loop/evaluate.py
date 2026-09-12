"""4-axis Discover rubric: module-fit, signal, license, actionability. Threshold ≥ 7."""

from __future__ import annotations

from typing import Any

from cost import MODULES

FREE_LICENSES = {
    "mit",
    "apache-2.0",
    "apache 2.0",
    "bsd",
    "bsd-3-clause",
    "bsd-2-clause",
    "postgresql",
    "mpl-2.0",
    "isc",
    "public",
    "unlicense",
}
CAVEAT_LICENSES = {"agpl-3.0", "agpl", "gpl-2.0", "gpl-3.0", "gpl"}
MODULE_NAMES = {f"cost/{name}" for name in MODULES} | {"cost/loop", "cost/audit"}

SIGNAL_TERMS = (
    ("cost", 2),
    ("data security posture", 3),
    ("pii", 2),
    ("presidio", 2),
    ("piicatcher", 2),
    ("dataprofiler", 2),
    ("cartography", 2),
    ("cloudsplaining", 2),
    ("gitleaks", 2),
    ("checkov", 2),
    ("osv-scanner", 2),
    ("duckdb", 1),
    ("prowler", 1),
    ("trivy", 1),
    ("cyera", 1),
    ("shadow data", 2),
    ("gdpr", 1),
)


def _blob(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(k) or "") for k in ("title", "summary", "source", "module_hint", "license", "name", "category")
    ).lower()


def axis_module_fit(item: dict[str, Any]) -> int:
    hint = str(item.get("module_hint") or item.get("module") or "")
    score = 0
    for name in MODULE_NAMES:
        if name in hint.lower() or name.split("/")[-1] in hint.lower():
            score = 4
            break
    if "cost" in hint.lower() and score == 0:
        score = 2
    return score


def axis_signal(item: dict[str, Any]) -> int:
    blob = _blob(item)
    raw = 0
    for term, weight in SIGNAL_TERMS:
        if term in blob:
            raw += weight
    return min(3, raw)


def axis_license(item: dict[str, Any]) -> int:
    lic = str(item.get("license") or "").lower().strip()
    blob = _blob(item)
    if any(tag in lic or tag in blob for tag in ("proprietary", "commercial", "purview", "wiz ", "prisma cloud")):
        return 0
    if lic in FREE_LICENSES or any(tag in blob for tag in ("apache-2.0", " mit", "bsd")):
        return 2
    if lic in CAVEAT_LICENSES or "agpl" in blob or "gpl" in blob:
        return 1
    return 1


def axis_actionability(item: dict[str, Any]) -> int:
    blob = _blob(item)
    score = 0
    if any(w in blob for w in ("release", "v0.", "v1.", "v2.", "changelog", "plugin")):
        score += 2
    if any(w in blob for w in ("pypi", "pip install", "stars", "apache", "mit")):
        score += 1
    if item.get("category") in {"github_tool", "python_lib"}:
        score += 1
    return min(3, score)


def evaluate_item(item: dict[str, Any]) -> dict[str, Any]:
    axes = {
        "module_fit": axis_module_fit(item),
        "signal": axis_signal(item),
        "license": axis_license(item),
        "actionability": axis_actionability(item),
    }
    total = sum(axes.values())
    if axes["license"] == 0:
        verdict = "skip"
    elif total >= 7:
        verdict = "discover"
    elif total >= 4:
        verdict = "watch"
    else:
        verdict = "skip"
    return {
        "verdict": verdict,
        "score": total,
        "axes": axes,
        "threshold": 7,
        "engine": "rubric-4axis",
    }
