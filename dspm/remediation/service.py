"""Cloud Custodian dry-run plans. Policies that take destructive action are never auto-merged."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from dspm.db.store import FindingsStore, utcnow
from dspm.remediation.models import RemediationAction
from dspm.tools import ToolError, run_cli

POLICIES_DIR = Path(__file__).with_name("policies")
MANUAL_REVIEW_PREFIX = "dspm/remediation/policies/"


def list_policies() -> list[Path]:
    return sorted(POLICIES_DIR.glob("c7n-*.yaml"))


def load_policy(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def plan(*, dry_run: bool = True, store: FindingsStore | None = None) -> list[RemediationAction]:
    actions: list[RemediationAction] = []
    for path in list_policies():
        raw = load_policy(path)
        policies = raw if isinstance(raw, list) else raw.get("policies") or [raw]
        for item in policies:
            name = str(item.get("name") or path.stem)
            resource = str(item.get("resource") or "unknown")
            actions.append(
                RemediationAction(
                    target=resource,
                    action=name,
                    policy=path.name,
                    preconditions=["dry-run" if dry_run else "operator-approved", "ci-green"],
                    risk_level=str(item.get("risk_level") or "high"),
                    dry_run_safe=True,
                    extra={"mode": item.get("mode"), "comments": item.get("comments")},
                )
            )
    if store is not None:
        for item in actions:
            store.insert(
                "remediation_plan",
                {
                    "target": item.target,
                    "action": item.action,
                    "policy": item.policy,
                    "preconditions": item.preconditions,
                    "risk_level": item.risk_level,
                    "dry_run_safe": item.dry_run_safe,
                    "extra": item.extra,
                    "created_at": utcnow(),
                },
            )
    return actions


def apply_policy(policy: str, *, limit: int = 5, dry_run: bool = True) -> dict[str, Any]:
    path = POLICIES_DIR / policy
    if not path.exists():
        matches = list(POLICIES_DIR.glob(f"*{policy}*"))
        path = matches[0] if matches else path
    if not path.exists():
        raise FileNotFoundError(policy)
    try:
        args = ["run", "-c", str(path), "--dryrun"] if dry_run else ["run", "-c", str(path)]
        proc = run_cli("c7n", args)
        return {
            "policy": path.name,
            "limit": limit,
            "dry_run": dry_run,
            "returncode": proc.returncode,
            "stdout_preview": (proc.stdout or "")[:500],
        }
    except ToolError as exc:
        return {
            "policy": path.name,
            "limit": limit,
            "dry_run": dry_run,
            "status": "offline-plan",
            "error": str(exc),
            "plan": json.loads(json.dumps([a.model_dump() for a in plan(dry_run=True) if path.name in a.policy])),
        }


def should_block_auto_merge(changed_files: list[str]) -> bool:
    return any(MANUAL_REVIEW_PREFIX in name.replace("\\", "/") for name in changed_files)
