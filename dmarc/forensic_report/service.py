"""Parse RUF / AFRF reports and mask mailbox identifiers before display."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dmarc.forensic_report.models import ForensicFinding
from dmarc.paths import RUF_FIXTURES
from dmarc.store import fetch_all, insert_rows, utcnow
from dmarc.xml_safe import ParseError
from dmarc.xml_safe import fromstring as xml_fromstring

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")


def mask_email(value: str) -> str:
    """Mask local-part. Presidio is optional; regex is the default $0 path."""
    if not value:
        return value
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig

        analyzer = AnalyzerEngine()
        anonymizer = AnonymizerEngine()
        results = analyzer.analyze(text=value, language="en")
        if results:
            return anonymizer.anonymize(
                text=value,
                analyzer_results=results,
                operators={"EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "***@***"})},
            ).text
    except Exception:
        return EMAIL_RE.sub(lambda m: f"{m.group(1)[:1]}***@{m.group(2)}", value)
    return EMAIL_RE.sub(lambda m: f"{m.group(1)[:1]}***@{m.group(2)}", value)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: Any | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _child(parent: Any, name: str) -> Any | None:
    for child in list(parent):
        if _local(child.tag) == name:
            return child
    return None


def _row_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("domain") or ""),
        str(row.get("source_ip") or ""),
        str(row.get("from_address") or ""),
        str(row.get("subject") or ""),
        str(row.get("dkim_result") or ""),
        str(row.get("spf_result") or ""),
    )


def parse_ruf_xml(xml_text: str, received_at: str | None = None) -> list[ForensicFinding]:
    root = xml_fromstring(xml_text)
    stamp = received_at or utcnow()
    findings: list[ForensicFinding] = []
    # AFRF (RFC 6591) uses feedback/incident. Walk incident/record only so the
    # wrapping <feedback> element is not counted as a second finding.
    incidents = [n for n in root.iter() if _local(n.tag) in {"incident", "record"}]
    if not incidents and _local(root.tag) == "feedback":
        incidents = [root]
    if not incidents:
        return findings
    for node in incidents:
        source_ip = ""
        from_addr = ""
        subject = ""
        dkim = "neutral"
        spf = "neutral"
        domain = ""
        source_el = _child(node, "source")
        source = source_el if source_el is not None else node
        source_ip = _text(_child(source, "ip_address")) or _text(_child(node, "source_ip"))
        from_addr = _text(_child(node, "envelope_from")) or _text(_child(node, "from"))
        subject = _text(_child(node, "subject"))
        dkim = _text(_child(node, "dkim")) or dkim
        spf = _text(_child(node, "spf")) or spf
        domain = _text(_child(node, "domain")) or (from_addr.split("@")[-1] if "@" in from_addr else "")
        if not (source_ip or from_addr or subject or domain):
            continue
        findings.append(
            ForensicFinding(
                domain=domain,
                source_ip=source_ip,
                from_address=mask_email(from_addr),
                subject=subject,
                dkim_result=dkim,
                spf_result=spf,
                received_at=stamp,
            )
        )
    return findings


def ingest_ruf_directory(directory: Path, root: Path | None = None, persist: bool = True) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    findings: list[ForensicFinding] = []
    for path in sorted(directory.glob("*.xml")):
        try:
            findings.extend(parse_ruf_xml(path.read_text(encoding="utf-8")))
        except ParseError:
            continue
    payload = [row.model_dump() for row in findings]
    if persist and payload:
        existing = {_row_key(row) for row in fetch_all("findings_forensic", root=root)}
        fresh = [row for row in payload if _row_key(row) not in existing]
        if fresh:
            insert_rows("findings_forensic", fresh, root)
        payload = fresh
    return payload


def ingest_ruf_fixtures(root: Path | None = None, persist: bool = True) -> list[dict[str, Any]]:
    return ingest_ruf_directory(RUF_FIXTURES, root=root, persist=persist)


def list_forensic(since: str = "30d", domain: str | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    from dmarc.aggregate_report.service import _since_cutoff

    if not fetch_all("findings_forensic", domain=domain, root=root):
        ingest_ruf_fixtures(root=root, persist=True)
    return fetch_all("findings_forensic", domain=domain, root=root, since=_since_cutoff(since))
