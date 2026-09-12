"""cost/rightsizing — heuristic observations. Never apply changes automatically."""

from __future__ import annotations

from typing import Any

from cost.adapters import list_resources
from cost.fixtures import tenant_id
from cost.persist import persist_named

REVIEW = "Review with the engineering team before applying any rightsizing change."

_DOWNSIZE = {
    "t3.large": "t3.small",
    "db.m5.xlarge": "db.m5.large",
    "Standard_D8s_v3": "Standard_D2s_v3",
    "n2-standard-8": "n2-standard-2",
}


def run(*, sandbox: bool = True, provider: str = "aws", **_kwargs: Any) -> dict[str, Any]:
    resources: list[dict[str, Any]] = []
    source = "sandbox"
    names = ("aws", "azure", "gcp") if provider == "all" else (provider,)
    for name in names:
        chunk, source = list_resources(name)
        resources.extend(chunk)
    findings = []
    for item in resources:
        cfg = item.get("config") or {}
        current = str(cfg.get("instance_type") or "")
        cpu = float(cfg.get("cpu_p95") or 100)
        attached = cfg.get("attached")
        associated = cfg.get("associated")
        recommended = None
        reason = ""
        risk = "low"
        savings = 0.0
        tags = item.get("tags") or {}
        env = str(tags.get("Environment") or tags.get("environment") or "").lower()
        if env in {"prod", "production"}:
            risk = "high"
        if current in _DOWNSIZE and cpu < 20:
            recommended = _DOWNSIZE[current]
            reason = f"p95 CPU {cpu}% suggests the current {current} is oversized"
            savings = round(float(item.get("monthly_cost") or 0) * 0.45, 2)
        elif attached is False or associated is False or cfg.get("status") == "RESERVED":
            recommended = "release-or-delete-after-review"
            reason = "idle address, volume, or IP with no attachment"
            savings = round(float(item.get("monthly_cost") or 0), 2)
            risk = "low"
        if recommended:
            findings.append(
                {
                    "tenant_id": tenant_id(),
                    "provider": item.get("provider"),
                    "resource_id": item.get("resource_id"),
                    "current_type": current or item.get("resource_type"),
                    "recommended_type": recommended,
                    "monthly_savings_estimate": savings,
                    "risk_level": risk,
                    "reason": reason,
                }
            )
    persist_named("findings_rightsizing", findings)
    return {
        "provider": provider,
        "source": source,
        "findings": findings,
        "review_with_engineering": REVIEW,
        "heuristic": True,
        "sandbox": sandbox,
    }
