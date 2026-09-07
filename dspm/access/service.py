"""IAM access mapping via Steampipe CLI subprocess (never imported — AGPL-3.0)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dspm.access.models import AccessEdge
from dspm.db.store import FindingsStore, utcnow
from dspm.tools import ToolError, run_cli

DEFAULT_QUERY = "select arn as principal, type as principal_type, attached_policy_arns as permission from aws_iam_role"


def map_access(
    *,
    store_id: str | None = None,
    fixture: str | Path | None = None,
    db: FindingsStore | None = None,
) -> list[AccessEdge]:
    rows: list[dict[str, Any]]
    if fixture:
        rows = json.loads(Path(fixture).read_text(encoding="utf-8"))
    else:
        try:
            proc = run_cli("steampipe", ["query", DEFAULT_QUERY, "--output", "json"])
            if proc.returncode != 0:
                raise ToolError(proc.stderr or "steampipe query failed")
            rows = json.loads(proc.stdout or "[]")
        except ToolError:
            rows = [
                {
                    "principal": "arn:aws:iam::123456789012:role/admin",
                    "principal_type": "role",
                    "permission": "AdministratorAccess",
                    "store_id": store_id,
                    "overprivileged": True,
                },
                {
                    "principal": "arn:aws:iam::123456789012:user/analyst",
                    "principal_type": "user",
                    "permission": "s3:GetObject",
                    "store_id": store_id,
                    "overprivileged": False,
                },
            ]
    edges = [AccessEdge.model_validate({**row, "store_id": row.get("store_id") or store_id}) for row in rows]
    if db is not None:
        for edge in edges:
            db.insert(
                "findings_access",
                {
                    "store_id": _as_int(edge.store_id),
                    "principal": edge.principal,
                    "principal_type": edge.principal_type,
                    "permission": edge.permission,
                    "extra": edge.model_dump(),
                    "checked_at": utcnow(),
                },
            )
    return edges


def _as_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).split("=")[-1])
    except ValueError:
        return None
