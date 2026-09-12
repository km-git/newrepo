"""Persist inventory rows into findings_* tables."""

from __future__ import annotations

from typing import Any

from cost.db.store import dumps, init_schema, replace_rows, upsert_tenant
from cost.fixtures import tenant_id, tenant_name


def persist_resources(resources: list[dict[str, Any]], source: str) -> int:
    conn = init_schema()
    tid = tenant_id()
    providers = sorted({str(r.get("provider") or "unknown") for r in resources}) or ["mixed"]
    upsert_tenant(conn, tid, tenant_name(), ",".join(providers))
    rows = []
    for item in resources:
        rows.append(
            {
                "tenant_id": tid,
                "provider": item.get("provider"),
                "account_id": item.get("account_id") or "",
                "region": item.get("region") or "",
                "resource_id": item.get("resource_id") or "",
                "resource_type": item.get("resource_type") or "",
                "name": item.get("name") or "",
                "tags_json": dumps(item.get("tags") or {}),
                "monthly_cost": float(item.get("monthly_cost") or 0),
                "config_json": dumps(item.get("config") or {}),
                "source": source,
            }
        )
    return replace_rows(conn, "findings_resources", rows)


def persist_named(table: str, rows: list[dict[str, Any]]) -> int:
    conn = init_schema()
    upsert_tenant(conn, tenant_id(), tenant_name(), "mixed")
    return replace_rows(conn, table, rows)
