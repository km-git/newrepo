"""Rightsizing recommendations — heuristic, review before applying."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cost.db.store import FindingsStore, utcnow

FIXTURE = Path(__file__).resolve().parents[2] / "examples" / "cost" / "rightsizing.json"


def scan(
    *,
    provider: str = "aws",
    fixture: Path | None = None,
    store: FindingsStore | None = None,
) -> dict[str, Any]:
    fx = fixture or FIXTURE
    items = __import__("json").loads(fx.read_text(encoding="utf-8"))
    db = store or FindingsStore()
    count = 0
    for row in items:
        if row.get("provider", provider) != provider:
            continue
        db.insert(
            "findings_rightsizing",
            {
                "provider": provider,
                "resource_id": row["resource_id"],
                "current_type": row["current_type"],
                "recommended_type": row["recommended_type"],
                "monthly_savings_estimate": float(row["monthly_savings_estimate"]),
                "risk_level": row.get("risk_level", "low"),
                "scanned_at": utcnow(),
            },
        )
        count += 1
    return {
        "provider": provider,
        "recommendations": count,
        "review_note": "Review with the engineering team before applying.",
        "honest_gap": "Rightsizing is heuristic; validate with workload metrics.",
    }
