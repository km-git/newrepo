"""Parse DMARC aggregate (RUA) XML / gzip / zip. IMAP optional via env secret."""

from __future__ import annotations

import contextlib
import gzip
import imaplib
import io
import os
import ssl
import zipfile
from email import message_from_bytes
from pathlib import Path
from typing import Any

from dmarc.dmarc_ingest.models import DmarcFinding
from dmarc.paths import RUA_FIXTURES
from dmarc.store import insert_rows, utcnow
from dmarc.xml_safe import ParseError
from dmarc.xml_safe import fromstring as xml_fromstring


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


def _find_text(parent: Any, *path: str) -> str:
    node: Any | None = parent
    for name in path:
        if node is None:
            return ""
        node = _child(node, name)
    return _text(node)


def parse_aggregate_xml(xml_text: str, received_at: str | None = None) -> list[DmarcFinding]:
    root = xml_fromstring(xml_text)
    org = _find_text(root, "report_metadata", "org_name")
    begin = _find_text(root, "report_metadata", "date_range", "begin")
    end = _find_text(root, "report_metadata", "date_range", "end")
    domain = _find_text(root, "policy_published", "domain")
    date_range = f"{begin}:{end}" if begin or end else ""
    stamp = received_at or utcnow()
    findings: list[DmarcFinding] = []
    for record in root.iter():
        if _local(record.tag) != "record":
            continue
        source_ip = _find_text(record, "row", "source_ip")
        count_raw = _find_text(record, "row", "count") or "0"
        try:
            count = int(count_raw)
        except ValueError:
            count = 0
        disposition = _find_text(record, "row", "policy_evaluated", "disposition") or "none"
        dkim = _find_text(record, "row", "policy_evaluated", "dkim") or "neutral"
        spf = _find_text(record, "row", "policy_evaluated", "spf") or "neutral"
        header_from = _find_text(record, "identifiers", "header_from") or domain
        findings.append(
            DmarcFinding(
                domain=header_from or domain,
                source_org=org,
                source_ip=source_ip,
                count=count,
                disposition=disposition,
                dkim_result=dkim,
                spf_result=spf,
                date_range=date_range,
                received_at=stamp,
            )
        )
    return findings


def _decode_bytes(blob: bytes) -> str:
    if blob.startswith(b"\x1f\x8b"):
        return gzip.decompress(blob).decode("utf-8", "replace")
    if blob[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            name = next((n for n in archive.namelist() if n.endswith(".xml")), archive.namelist()[0])
            return archive.read(name).decode("utf-8", "replace")
    return blob.decode("utf-8", "replace")


def parse_report_file(path: Path) -> list[DmarcFinding]:
    return parse_aggregate_xml(_decode_bytes(path.read_bytes()))


def ingest_directory(directory: Path, root: Path | None = None, persist: bool = True) -> list[dict[str, Any]]:
    findings: list[DmarcFinding] = []
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() not in {".xml", ".gz", ".zip"} and not path.name.endswith(".xml.gz"):
            continue
        findings.extend(parse_report_file(path))
    payload = [row.model_dump() for row in findings]
    if persist and payload:
        insert_rows("findings_dmarc", payload, root)
    return payload


def ingest_fixtures(root: Path | None = None) -> list[dict[str, Any]]:
    rows = ingest_directory(RUA_FIXTURES, root=root)
    from dmarc.forensic_report.service import ingest_ruf_fixtures

    ingest_ruf_fixtures(root=root)
    return rows


def ingest_imap(
    host: str,
    user: str,
    password: str | None = None,
    folder: str = "INBOX",
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """Pull RUA attachments from IMAP. Password from DMARC_IMAP_PASS only."""
    secret = password or os.environ.get("DMARC_IMAP_PASS") or ""
    if not secret:
        raise RuntimeError("DMARC_IMAP_PASS is not set; refusing to bind a plaintext password")
    findings: list[DmarcFinding] = []
    client = imaplib.IMAP4_SSL(host, ssl_context=ssl.create_default_context())
    try:
        client.login(user, secret)
        client.select(folder)
        _, data = client.search(None, "ALL")
        ids = (data[0] or b"").split()
        for msg_id in ids:
            _, fetched = client.fetch(msg_id, "(RFC822)")
            if not fetched or fetched[0] is None:
                continue
            raw = fetched[0][1]
            message = message_from_bytes(raw)
            for part in message.walk():
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                name = (part.get_filename() or "").lower()
                if name.endswith((".xml", ".gz", ".zip", ".xml.gz")) or payload[:5].lstrip().startswith(b"<?xml"):
                    try:
                        findings.extend(parse_aggregate_xml(_decode_bytes(payload)))
                    except ParseError:
                        continue
    finally:
        with contextlib.suppress(Exception):
            client.logout()
    payload = [row.model_dump() for row in findings]
    if payload:
        insert_rows("findings_dmarc", payload, root)
    return payload
