"""Observability — Datadog-inspired metrics, alerts, health."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from dspm.store.db import fetch_all, init_db, insert_row

DEFAULT_ALERT_RULES = [
    {"name": "high_risk_finding", "condition": "risk_score >= 90", "threshold": 90.0},
    {"name": "critical_exposure", "condition": "exposure_severity == critical", "threshold": 1.0},
    {"name": "pii_spike", "condition": "pii_findings_per_hour > 10", "threshold": 10.0},
]


def record_metric(name: str, value: float, labels: dict | None = None) -> dict[str, Any]:
    init_db()
    now = datetime.now(UTC).isoformat()
    row = {
        "metric_name": name,
        "value": value,
        "labels": json.dumps(labels or {}),
        "created_at": now,
    }
    mid = insert_row("observability_metrics", row)
    return {"id": mid, **row}


def seed_alert_rules() -> list[dict]:
    init_db()
    if fetch_all("alert_rules", limit=1):
        return fetch_all("alert_rules", limit=20)
    now = datetime.now(UTC).isoformat()
    for rule in DEFAULT_ALERT_RULES:
        insert_row(
            "alert_rules",
            {
                "name": rule["name"],
                "condition": rule["condition"],
                "threshold": rule["threshold"],
                "enabled": 1,
                "created_at": now,
            },
        )
    return fetch_all("alert_rules", limit=20)


def dashboard_summary(findings: list[dict], risks: list[dict], exposures: list[dict]) -> dict[str, Any]:
    avg_risk = sum(r.get("score", 0) for r in risks) / max(len(risks), 1)
    critical_exp = sum(1 for e in exposures if e.get("severity") == "critical")
    pii_count = sum(1 for f in findings if f.get("type") in {"PII", "PHI", "PCI"})
    metrics = {
        "findings_total": len(findings),
        "pii_findings": pii_count,
        "avg_risk_score": round(avg_risk, 1),
        "critical_exposures": critical_exp,
        "health": "healthy" if critical_exp == 0 else "degraded",
    }
    for k, v in metrics.items():
        if isinstance(v, int | float):
            record_metric(k, float(v))
    return metrics


def evaluate_alerts(metrics: dict[str, float]) -> list[dict]:
    rules = seed_alert_rules()
    fired = []
    for rule in rules:
        if not rule.get("enabled"):
            continue
        name = rule["name"]
        threshold = float(rule["threshold"])
        if name == "high_risk_finding" and metrics.get("avg_risk_score", 0) >= threshold:
            fired.append({**rule, "status": "firing", "current": metrics.get("avg_risk_score")})
        if name == "critical_exposure" and metrics.get("critical_exposures", 0) >= threshold:
            fired.append({**rule, "status": "firing", "current": metrics.get("critical_exposures")})
        if name == "pii_spike" and metrics.get("pii_findings", 0) >= threshold:
            fired.append({**rule, "status": "firing", "current": metrics.get("pii_findings")})
    return fired
