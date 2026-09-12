"""IAM access mapping via Steampipe subprocess."""

from __future__ import annotations

import json
from pathlib import Path

from dspm._cli_tools import run_cli

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def map_access(store_id: int | None = None) -> list[dict]:
    fixture = FIXTURES / "steampipe_access.json"
    try:
        raw = run_cli(["steampipe", "query", "select * from aws_iam_role"], fixture_path=fixture)
    except Exception:
        raw = json.loads(fixture.read_text(encoding="utf-8")) if fixture.exists() else []
    items = raw if isinstance(raw, list) else raw.get("rows", [])
    mappings: list[dict] = []
    for item in items:
        mappings.append(
            {
                "principal": item.get("principal", item.get("role_name", "unknown")),
                "store_id": store_id or item.get("store_id", 42),
                "permission": item.get("permission", item.get("policy", "read")),
            }
        )
    return mappings
