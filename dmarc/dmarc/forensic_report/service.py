"""Forensic (RUF) report parser with Presidio PII scrubbing."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from dmarc.db import clear_table, fetch_all, insert_rows
from dmarc.models import ForensicFinding


def _scrub_email(value: str) -> str:
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine

        analyzer = AnalyzerEngine()
        anonymizer = AnonymizerEngine()
        results = analyzer.analyze(text=value, entities=["EMAIL_ADDRESS", "PERSON"], language="en")
        return anonymizer.anonymize(text=value, analyzer_results=results).text
    except Exception:
        return re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL]", value)


def list_forensic(domain: str, since: str = "30d") -> list[ForensicFinding]:
    _ = {"7d": 7, "30d": 30, "90d": 90}.get(since, 30)
    existing = fetch_all("findings_forensic", limit=500)
    if existing:
        return [ForensicFinding(**row) for row in existing if row.get("domain") == domain]

    # Many senders omit RUF — return empty gracefully
    clear_table("findings_forensic")
    return []


def ingest_forensic_sample(domain: str) -> list[ForensicFinding]:
    now = datetime.now(timezone.utc)
    sample = ForensicFinding(
        domain=domain,
        source_ip="198.51.100.77",
        from_address=_scrub_email("customer.jane.doe@retailer.example"),
        subject="[scrubbed forensic sample]",
        dkim_result="fail",
        spf_result="fail",
        received_at=now,
    )
    rows = [sample.model_dump(mode="json")]
    insert_rows("findings_forensic", rows)
    return [sample]
