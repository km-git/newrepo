"""Risk scoring via DuckDB SQL over findings."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from dspm.models import Finding, RiskScore

WEIGHTS = {
    "PII": 30,
    "PHI": 30,
    "PCI": 30,
    "public_exposure": 25,
    "over_privileged": 20,
    "encryption": 15,
    "custom": 10,
    "secret": 35,
    "IP": 10,
}


def score_findings(
    findings: list[Finding],
    exposures: list[dict] | None = None,
) -> list[RiskScore]:
    conn = duckdb.connect(":memory:")
    rows = [(i + 1, f.type, f.confidence, f.verdict, f.source, f.location) for i, f in enumerate(findings)]
    conn.execute(
        "CREATE TABLE findings (id INTEGER, type VARCHAR, confidence DOUBLE, verdict VARCHAR, source VARCHAR, location VARCHAR)"
    )
    if rows:
        conn.executemany("INSERT INTO findings VALUES (?, ?, ?, ?, ?, ?)", rows)
    exp_bonus = 25 if exposures else 0
    sql = f"""
    SELECT
        id AS finding_id,
        LEAST(100.0,
            CASE type
                WHEN 'PII' THEN {WEIGHTS['PII']}
                WHEN 'PHI' THEN {WEIGHTS['PHI']}
                WHEN 'PCI' THEN {WEIGHTS['PCI']}
                WHEN 'secret' THEN {WEIGHTS['secret']}
                WHEN 'IP' THEN {WEIGHTS['IP']}
                ELSE {WEIGHTS['custom']}
            END * confidence
            + CASE WHEN verdict = 'public' THEN {WEIGHTS['public_exposure']} ELSE 0 END
            + {exp_bonus}
            + CASE WHEN type IN ('PII', 'PHI', 'PCI') AND {exp_bonus} > 0 THEN 20 ELSE 0 END
        ) AS score,
        type || ':' || location AS vector
    FROM findings
    ORDER BY score DESC
    """
    result = conn.execute(sql).fetchall()
    scores: list[RiskScore] = []
    for fid, score, vector in result:
        action = "revoke public access" if score >= 90 else "review and remediate"
        scores.append(RiskScore(finding_id=int(fid), score=float(score), vector=str(vector), suggested_action=action))
    return scores


def score_from_fixture(fixture_path: Path) -> list[RiskScore]:
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    findings = [Finding(**f) for f in data.get("findings", [])]
    exposures = data.get("exposures", [])
    return score_findings(findings, exposures)


def risks_to_dict(scores: list[RiskScore]) -> list[dict]:
    return [s.model_dump() for s in scores]
