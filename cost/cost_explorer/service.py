"""Cost rollup via DuckDB across provider fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb

from cost.db.store import FindingsStore, utcnow

FIXTURE = Path(__file__).resolve().parents[2] / "examples" / "cost" / "cost_lines.json"


def explore(
    *,
    provider: str = "aws",
    since: str = "30d",
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    fx = fixture or FIXTURE
    lines = __import__("json").loads(fx.read_text(encoding="utf-8"))
    days = int(since.rstrip("d") or "30")
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days)
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE costs(provider VARCHAR, service VARCHAR, region VARCHAR, "
        "tag_key VARCHAR, tag_value VARCHAR, amount DOUBLE)"
    )
    for row in lines:
        if row.get("provider", provider) != provider:
            continue
        con.execute(
            "INSERT INTO costs VALUES (?, ?, ?, ?, ?, ?)",
            [
                row["provider"],
                row["service"],
                row.get("region", "global"),
                row.get("tag_key"),
                row.get("tag_value"),
                float(row["amount"]),
            ],
        )
    rollup = con.execute(
        """
        SELECT provider, service, region, SUM(amount) AS total
        FROM costs GROUP BY 1,2,3 ORDER BY total DESC
        """
    ).fetchall()
    db = store or FindingsStore()
    count = 0
    for prov, service, region, total in rollup:
        db.insert(
            "findings_costs",
            {
                "provider": prov,
                "service": service,
                "region": region or "global",
                "amount": float(total),
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "recorded_at": utcnow(),
            },
        )
        count += 1
    lag_note = "Cost data has a 24-48h lag; not real-time."
    return {
        "provider": provider,
        "since": since,
        "rollup_rows": count,
        "top_services": [{"service": r[1], "region": r[2], "total": float(r[3])} for r in rollup[:5]],
        "honest_gap": lag_note,
    }
