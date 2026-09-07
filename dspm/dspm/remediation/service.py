"""Remediation planning via Cloud Custodian policies."""

from __future__ import annotations

import json
from pathlib import Path

from dspm.models import RemediationAction

POLICIES_DIR = Path(__file__).resolve().parent / "policies"

DEFAULT_POLICIES = [
    RemediationAction(
        target="s3://public-bucket/*",
        action="revoke-public-access",
        preconditions={"exposure": "public"},
        risk_level="high",
        dry_run_safe=True,
    ),
    RemediationAction(
        target="rds:unencrypted-instance",
        action="enable-encryption",
        preconditions={"encrypted": False},
        risk_level="medium",
        dry_run_safe=True,
    ),
    RemediationAction(
        target="s3://pii-bucket/*",
        action="mask-pii",
        preconditions={"contains_pii": True},
        risk_level="high",
        dry_run_safe=True,
    ),
    RemediationAction(
        target="s3://shadow-bucket",
        action="alert-operator",
        preconditions={"shadow": True},
        risk_level="low",
        dry_run_safe=True,
    ),
]


def build_plan(dry_run: bool = True) -> list[dict]:
    plan = [p.model_dump() for p in DEFAULT_POLICIES]
    if dry_run:
        for item in plan:
            item["mode"] = "dry-run"
    return plan


def write_plan(out_path: Path, dry_run: bool = True) -> list[dict]:
    plan = build_plan(dry_run)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan


def list_policies() -> list[str]:
    if POLICIES_DIR.exists():
        return [p.name for p in POLICIES_DIR.glob("*.yaml")]
    return []
