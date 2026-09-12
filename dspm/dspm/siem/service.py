"""SIEM — Splunk-inspired event search and correlation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from dspm.store.db import fetch_all, init_db, insert_row

ATTACK_CHAINS = [
    {"name": "public_s3_pii", "pattern": ["exposure", "classification"], "severity": "critical"},
    {"name": "shadow_unencrypted", "pattern": ["shadow", "encryption"], "severity": "high"},
]


def ingest_event(
    event_type: str,
    severity: str,
    source: str,
    message: str,
    raw: dict | None = None,
) -> dict[str, Any]:
    init_db()
    now = datetime.now(UTC).isoformat()
    row = {
        "event_type": event_type,
        "severity": severity,
        "source": source,
        "message": message,
        "raw": json.dumps(raw or {}),
        "created_at": now,
    }
    eid = insert_row("siem_events", row)
    return {"id": eid, **row}


def search_events(query: str, limit: int = 50) -> list[dict]:
    events = fetch_all("siem_events", limit=500)
    if not query or query == "*":
        return events[:limit]
    needle = query.casefold()
    matched = [
        e
        for e in events
        if needle in e.get("message", "").casefold()
        or needle in e.get("event_type", "").casefold()
        or needle in e.get("source", "").casefold()
    ]
    return matched[:limit]


def correlate_findings(findings: list[dict], exposures: list[dict]) -> list[dict]:
    alerts = []
    has_pii = any(f.get("type") in {"PII", "PHI", "PCI"} for f in findings)
    has_public = any("public" in e.get("exposure_type", "").lower() for e in exposures)
    if has_pii and has_public:
        alert = ingest_event(
            "correlation",
            "critical",
            "dspm/siem",
            "Attack chain detected: public exposure + sensitive data (public_s3_pii)",
            {"chain": "public_s3_pii", "finding_count": len(findings), "exposure_count": len(exposures)},
        )
        alerts.append(alert)
    return alerts


def normalize_to_ecs(event: dict) -> dict:
    return {
        "@timestamp": event.get("created_at"),
        "event.kind": "alert",
        "event.category": [event.get("event_type", "unknown")],
        "event.severity": event.get("severity"),
        "message": event.get("message"),
        "source.ip": event.get("source"),
    }
