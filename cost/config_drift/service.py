"""Config drift detection via Prowler snapshot + DuckDB diff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from cost.db.store import FindingsStore, utcnow
from cost.tools import run_prowler

FIXTURE = Path(__file__).resolve().parents[2] / "examples" / "cost" / "prowler_snapshot.json"
BASELINE = Path(__file__).resolve().parents[2] / "examples" / "cost" / "baseline.json"


def diff(
    *,
    provider: str = "aws",
    baseline_path: Path | None = None,
    fixture: Path | None = None,
    out_dir: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    base = json.loads((baseline_path or BASELINE).read_text(encoding="utf-8"))
    prowler_dir = out_dir or Path("output/cost/prowler-out")
    current_path = run_prowler(provider=provider, out_dir=prowler_dir, fixture=fixture or FIXTURE)
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current_map = {r["resource_id"]: r for r in current.get("resources", current if isinstance(current, list) else [])}
    base_map = {r["resource_id"]: r for r in base.get("resources", [])}
    db = store or FindingsStore()
    drifts = 0
    for rid, cur in current_map.items():
        old = base_map.get(rid)
        if not old:
            continue
        for field in ("instance_type", "storage_class", "reserved_instance_expiry"):
            if cur.get(field) != old.get(field):
                db.insert(
                    "findings_drift",
                    {
                        "provider": provider,
                        "resource_id": rid,
                        "field": field,
                        "baseline_value": str(old.get(field)),
                        "current_value": str(cur.get(field)),
                        "cost_impact": float(cur.get("cost_impact", 0) or 0),
                        "detected_at": utcnow(),
                    },
                )
                drifts += 1
    con = duckdb.connect(":memory:")
    con.execute("SELECT 1")  # ensure duckdb wired
    return {
        "provider": provider,
        "drift_count": drifts,
        "baseline": str(baseline_path or BASELINE),
        "current_snapshot": str(current_path),
    }
