"""AWS inventory via Steampipe CLI subprocess + boto3 fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cost.db.store import FindingsStore, utcnow
from cost.tools import run_steampipe_query

FIXTURE = Path(__file__).resolve().parents[2] / "examples" / "cost" / "aws_resources.json"


def scan_aws(
    *,
    profile: str | None = None,
    regions: list[str] | None = None,
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    fx = fixture or FIXTURE
    rows = run_steampipe_query("select * from aws_ec2_instance limit 100", fixture=fx)
    db = store or FindingsStore()
    count = 0
    for row in rows:
        db.insert(
            "findings_resources",
            {
                "provider": "aws",
                "region": row.get("region", regions[0] if regions else "ap-southeast-2"),
                "resource_id": row.get("instance_id") or row.get("arn") or row.get("title", "unknown"),
                "resource_type": row.get("resource_type", "ec2"),
                "tags": row.get("tags", {}),
                "monthly_cost": float(row.get("monthly_cost", 0) or 0),
                "discovered_at": utcnow(),
            },
        )
        count += 1
    return {
        "provider": "aws",
        "profile": profile,
        "regions": regions or ["ap-southeast-2"],
        "resource_count": count,
        "fixture": str(fx),
    }
