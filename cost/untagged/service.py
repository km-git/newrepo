"""cost/untagged — organisational tagging gaps, not a technical defect."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cost.adapters import list_resources
from cost.fixtures import tenant_id
from cost.paths import TAGGING_POLICY_PATH
from cost.persist import persist_named

ORG_NOTE = "Untagged resources are an organisational problem; review with the team that owns the account."


def load_policy(path: str | Path | None = None) -> list[str]:
    target = Path(path) if path else TAGGING_POLICY_PATH
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    tags = data.get("required_tags") or ["Environment", "CostCenter", "Owner"]
    return [str(t) for t in tags]


def _tag_lookup(tags: dict[str, Any]) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in (tags or {}).items()}


def run(*, sandbox: bool = True, tagging_policy: str = "", provider: str = "all", **_kwargs: Any) -> dict[str, Any]:
    required = load_policy(tagging_policy or None)
    resources: list[dict[str, Any]] = []
    source = "sandbox"
    providers = ("aws", "azure", "gcp") if provider == "all" else (provider,)
    for name in providers:
        chunk, source = list_resources(name)
        resources.extend(chunk)
    findings = []
    for item in resources:
        lookup = _tag_lookup(item.get("tags") or {})
        missing = [tag for tag in required if tag.lower() not in lookup or not lookup[tag.lower()]]
        if missing:
            findings.append(
                {
                    "tenant_id": tenant_id(),
                    "provider": item.get("provider"),
                    "resource_id": item.get("resource_id"),
                    "resource_type": item.get("resource_type"),
                    "missing_tags": ",".join(missing),
                    "monthly_cost": float(item.get("monthly_cost") or 0),
                }
            )
    persist_named("findings_untagged", findings)
    return {
        "required_tags": required,
        "findings": findings,
        "organisational_note": ORG_NOTE,
        "source": source,
        "sandbox": sandbox,
        "policy": str(tagging_policy or TAGGING_POLICY_PATH),
    }
