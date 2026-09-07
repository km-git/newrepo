"""Deterministic DuckDB-equivalent risk scoring over findings ∪ exposures."""

from __future__ import annotations

import json
from typing import Any

from dspm.constants import RISK_WEIGHTS
from dspm.db.store import FindingsStore, utcnow
from dspm.risk.models import Risk

SQL_VIEW = """
-- Canonical risk formula (DuckDB / SQLite-compatible).
-- weights: PII=30, public=25, overprivileged=20, unencrypted=15, custom=10
-- blast-radius bonus=20 when PII/PHI/PCI/custom AND public exposure.
SELECT
  finding_id,
  LEAST(100,
    (CASE WHEN has_pii THEN 30 ELSE 0 END) +
    (CASE WHEN public_exposure THEN 25 ELSE 0 END) +
    (CASE WHEN overprivileged THEN 20 ELSE 0 END) +
    (CASE WHEN unencrypted THEN 15 ELSE 0 END) +
    (CASE WHEN custom_type THEN 10 ELSE 0 END) +
    (CASE WHEN has_pii AND public_exposure THEN 20 ELSE 0 END)
  ) AS score
FROM risk_input
"""


def score_vector(
    *,
    has_pii: bool = False,
    public_exposure: bool = False,
    overprivileged: bool = False,
    unencrypted: bool = False,
    custom_type: bool = False,
) -> dict[str, Any]:
    parts = {
        "pii": RISK_WEIGHTS["pii"] if has_pii else 0,
        "public_exposure": RISK_WEIGHTS["public_exposure"] if public_exposure else 0,
        "overprivileged": RISK_WEIGHTS["overprivileged"] if overprivileged else 0,
        "unencrypted": RISK_WEIGHTS["unencrypted"] if unencrypted else 0,
        "custom": RISK_WEIGHTS["custom"] if custom_type else 0,
        "blast_radius_bonus": RISK_WEIGHTS["blast_radius_bonus"] if (has_pii and public_exposure) else 0,
    }
    score = min(100, sum(parts.values()))
    return {"score": score, "vector": parts}


def _flags_from_finding(row: dict[str, Any], exposures: list[dict[str, Any]]) -> dict[str, bool]:
    ftype = str(row.get("type") or "")
    extra = row.get("extra") or {}
    if isinstance(extra, str):
        extra = json.loads(extra) if extra else {}
    public = any(bool(item.get("public")) for item in exposures) or bool(extra.get("public"))
    return {
        "has_pii": ftype in {"PII", "PHI", "PCI"} or extra.get("has_pii") is True,
        "public_exposure": public,
        "overprivileged": bool(extra.get("overprivileged")),
        "unencrypted": bool(extra.get("unencrypted")),
        "custom_type": ftype == "custom",
    }


def score_findings(
    findings: list[dict[str, Any]],
    *,
    exposures: list[dict[str, Any]] | None = None,
    store: FindingsStore | None = None,
) -> list[Risk]:
    exposures = exposures or []
    ranked: list[Risk] = []
    for row in findings:
        flags = _flags_from_finding(row, exposures)
        computed = score_vector(**flags)
        finding_id = str(row.get("id") or row.get("finding_id") or row.get("source") or "unknown")
        action = "prioritize remediation" if computed["score"] >= 70 else "review"
        if flags["public_exposure"] and flags["has_pii"]:
            action = "revoke public access and mask PII"
        item = Risk(
            finding_id=finding_id,
            score=int(computed["score"]),
            vector=computed["vector"],
            suggested_action=action,
            title=_title(row, flags),
        )
        ranked.append(item)
        if store is not None:
            store.insert(
                "findings_risk",
                {
                    "finding_id": row.get("id") or 0,
                    "score": item.score,
                    "vector": item.vector,
                    "suggested_action": item.suggested_action,
                    "scored_at": utcnow(),
                },
            )
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


def score_store(store: FindingsStore) -> list[Risk]:
    findings = store.fetchall("findings")
    exposures = store.fetchall("findings_exposure")
    return score_findings(findings, exposures=exposures, store=store)


def try_duckdb_score(rows: list[dict[str, Any]]) -> list[int] | None:
    """Same formula in DuckDB when the optional package is installed."""
    try:
        import duckdb  # type: ignore[import-not-found]
    except ImportError:
        return None
    conn = duckdb.connect(database=":memory:")
    conn.execute(
        "CREATE TABLE risk_input (finding_id VARCHAR, has_pii BOOLEAN, public_exposure BOOLEAN, "
        "overprivileged BOOLEAN, unencrypted BOOLEAN, custom_type BOOLEAN)"
    )
    for row in rows:
        conn.execute(
            "INSERT INTO risk_input VALUES (?, ?, ?, ?, ?, ?)",
            [
                row["finding_id"],
                row["has_pii"],
                row["public_exposure"],
                row["overprivileged"],
                row["unencrypted"],
                row["custom_type"],
            ],
        )
    result = conn.execute(SQL_VIEW).fetchall()
    return [int(r[1]) for r in result]


def _title(row: dict[str, Any], flags: dict[str, bool]) -> str:
    loc = row.get("location") or row.get("source") or "asset"
    bits = []
    if flags["public_exposure"]:
        bits.append("public")
    bits.append(str(row.get("type") or "finding"))
    return f"{' '.join(bits)} at {loc}"
