"""Azure subscription inventory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cost.db.store import FindingsStore, utcnow
from cost.tools import run_steampipe_query

FIXTURE = Path(__file__).resolve().parents[2] / "examples" / "cost" / "azure_resources.json"


def scan_azure(
    *,
    subscription_id: str | None = None,
    tenant_id: str | None = None,
    client_id: str | None = None,
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    fx = fixture or FIXTURE
    rows = run_steampipe_query("select * from azure_compute_virtual_machine", fixture=fx)
    db = store or FindingsStore()
    count = 0
    for row in rows:
        db.insert(
            "findings_resources",
            {
                "provider": "azure",
                "region": row.get("location", "australiaeast"),
                "resource_id": row.get("id") or row.get("name", "unknown"),
                "resource_type": row.get("type", "vm"),
                "tags": row.get("tags", {}),
                "monthly_cost": float(row.get("monthly_cost", 0) or 0),
                "discovered_at": utcnow(),
            },
        )
        count += 1
    return {
        "provider": "azure",
        "subscription_id": subscription_id,
        "resource_count": count,
        "fixture": str(fx),
    }
