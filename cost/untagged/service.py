"""Untagged resource inventory against tagging policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cost.db.store import FindingsStore, utcnow

DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "cost" / "remediation" / "tagging-policy.yaml"
FIXTURE = Path(__file__).resolve().parents[2] / "examples" / "cost" / "untagged.json"


def scan(
    *,
    policy_path: Path | None = None,
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    policy_file = policy_path or DEFAULT_POLICY
    policy = yaml.safe_load(policy_file.read_text(encoding="utf-8")) or {}
    required = list(policy.get("required_tags", ["Environment", "CostCenter", "Owner"]))
    fx = fixture or FIXTURE
    items = __import__("json").loads(fx.read_text(encoding="utf-8"))
    db = store or FindingsStore()
    count = 0
    for row in items:
        missing = [t for t in required if t not in (row.get("tags") or {})]
        if not missing:
            continue
        db.insert(
            "findings_untagged",
            {
                "provider": row.get("provider", "aws"),
                "resource_id": row["resource_id"],
                "resource_type": row.get("resource_type", "unknown"),
                "missing_tags": missing,
                "monthly_cost": float(row.get("monthly_cost", 0)),
                "scanned_at": utcnow(),
            },
        )
        count += 1
    return {
        "required_tags": required,
        "untagged_count": count,
        "review_note": "Review with the team that owns the account.",
        "honest_gap": "Untagged resources are an organisational problem, not purely technical.",
    }
