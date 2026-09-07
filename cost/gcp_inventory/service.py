"""GCP project inventory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cost.db.store import FindingsStore, utcnow
from cost.tools import run_steampipe_query

FIXTURE = Path(__file__).resolve().parents[2] / "examples" / "cost" / "gcp_resources.json"


def scan_gcp(
    *,
    project_id: str | None = None,
    service_account: str | None = None,
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    fx = fixture or FIXTURE
    rows = run_steampipe_query("select * from gcp_compute_instance", fixture=fx)
    db = store or FindingsStore()
    count = 0
    for row in rows:
        db.insert(
            "findings_resources",
            {
                "provider": "gcp",
                "region": row.get("zone", "australia-southeast1-a"),
                "resource_id": row.get("name") or row.get("self_link", "unknown"),
                "resource_type": row.get("kind", "compute.instance"),
                "tags": row.get("labels", {}),
                "monthly_cost": float(row.get("monthly_cost", 0) or 0),
                "discovered_at": utcnow(),
            },
        )
        count += 1
    return {
        "provider": "gcp",
        "project_id": project_id,
        "resource_count": count,
        "fixture": str(fx),
    }
