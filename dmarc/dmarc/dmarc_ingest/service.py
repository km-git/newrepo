"""DMARC aggregate report (RUA) ingester."""

from __future__ import annotations

import gzip
import io
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from dmarc.config import SAMPLES_DIR
from dmarc.db import clear_table, insert_rows
from dmarc.models import DmarcAggregateFinding


def _parse_aggregate_xml(xml_bytes: bytes, domain: str) -> list[DmarcAggregateFinding]:
    root = ET.fromstring(xml_bytes)
    ns = {"dmarc": "urn:ietf:params:xml:ns:dmarc-2.0"}
    if root.tag.endswith("feedback"):
        ns = {}

    def find(path: str) -> ET.Element | None:
        for prefix in ("", "dmarc:"):
            el = root.find(path.replace("dmarc:", prefix), ns if prefix else {})
            if el is not None:
                return el
        return None

    report_domain = find(".//report_metadata/org_name")
    if report_domain is None:
        report_domain = find(".//org_name")
    org = report_domain.text if report_domain is not None else "unknown"
    begin = find(".//date_range/begin")
    end = find(".//date_range/end")
    date_range = f"{begin.text}-{end.text}" if begin is not None and end is not None else "unknown"
    now = datetime.now(timezone.utc)
    findings: list[DmarcAggregateFinding] = []

    records = root.findall(".//record") or root.findall(".//{*}record")
    for rec in records:
        source_ip = rec.findtext(".//source_ip") or rec.findtext(".//{*}source_ip") or "0.0.0.0"
        count = int(rec.findtext(".//count") or rec.findtext(".//{*}count") or "0")
        policy = rec.find(".//policy_evaluated")
        if policy is None:
            policy = rec.find(".//{*}policy_evaluated")
        disposition = policy.findtext("disposition") if policy is not None else "none"
        dkim = policy.findtext("dkim") if policy is not None else "neutral"
        spf = policy.findtext("spf") if policy is not None else "neutral"
        findings.append(
            DmarcAggregateFinding(
                domain=domain,
                source_org=org,
                source_ip=source_ip,
                count=count,
                disposition=disposition or "none",
                dkim_result=dkim or "neutral",
                spf_result=spf or "neutral",
                date_range=date_range,
                received_at=now,
            )
        )
    return findings


def _load_archive(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix == ".gz":
        return gzip.decompress(data)
    if path.suffix == ".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name.endswith(".xml"):
                    return zf.read(name)
    return data


def ingest_samples(domain: str) -> list[DmarcAggregateFinding]:
    sample_dir = SAMPLES_DIR / "rua"
    findings: list[DmarcAggregateFinding] = []
    if sample_dir.is_dir():
        for path in sorted(sample_dir.glob("*")):
            if path.suffix in {".xml", ".gz", ".zip"}:
                findings.extend(_parse_aggregate_xml(_load_archive(path), domain))
    return findings


def pull_imap(domain: str) -> list[DmarcAggregateFinding]:
    """Pull RUA reports from IMAP when credentials are set; else load samples."""
    host = os.environ.get("DMARC_IMAP_HOST")
    user = os.environ.get("DMARC_IMAP_USER")
    password = os.environ.get("DMARC_IMAP_PASS")
    if not all([host, user, password]):
        return ingest_samples(domain)

    import imaplib

    findings: list[DmarcAggregateFinding] = []
    mail = imaplib.IMAP4_SSL(host)
    mail.login(user, password)
    mail.select("INBOX")
    _, data = mail.search(None, "UNSEEN")
    for num in (data[0] or b"").split():
        _, msg_data = mail.fetch(num, "(RFC822)")
        if not msg_data or not msg_data[0]:
            continue
        payload = msg_data[0][1]
        if b"<feedback" in payload or b"aggregate" in payload.lower():
            start = payload.find(b"<?xml")
            if start >= 0:
                end = payload.find(b"</feedback>") + len(b"</feedback>")
                xml = payload[start:end]
                findings.extend(_parse_aggregate_xml(xml, domain))
    mail.logout()
    return findings


def ingest_reports(domain: str, *, demo: bool = False) -> list[DmarcAggregateFinding]:
    findings = ingest_samples(domain) if demo else pull_imap(domain)
    clear_table("findings_dmarc")
    rows = [f.model_dump(mode="json") for f in findings]
    insert_rows("findings_dmarc", rows)
    return findings
