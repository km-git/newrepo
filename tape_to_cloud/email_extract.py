"""Stdlib .eml / .mbox extract (custodian / date / keyword). Not PST/NSF."""

from __future__ import annotations

import mailbox
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any


def _plain_text(part: Any) -> str:
    try:
        content = part.get_content() if hasattr(part, "get_content") else part.get_payload()
    except (LookupError, KeyError, ValueError, UnicodeError, AttributeError):
        content = part.get_payload(decode=False)
    if content is None:
        return ""
    return content if isinstance(content, str) else str(content)


def _message_record(msg: Any, source: str, keyword: str | None) -> dict[str, Any] | None:
    if msg.is_multipart():
        body = "".join(_plain_text(part) for part in msg.walk() if part.get_content_type() == "text/plain")
    else:
        body = _plain_text(msg)
    blob = f"{msg.get('from', '')}\n{msg.get('to', '')}\n{msg.get('subject', '')}\n{body}"
    if keyword and keyword.lower() not in blob.lower():
        return None
    date_raw = msg.get("date")
    date_iso = None
    if date_raw:
        try:
            date_iso = parsedate_to_datetime(date_raw).isoformat()
        except (TypeError, ValueError, IndexError):
            date_iso = str(date_raw)
    return {
        "source": source,
        "from": msg.get("from"),
        "to": msg.get("to"),
        "subject": msg.get("subject"),
        "date": date_iso,
        "message_id": msg.get("message-id"),
        "keyword_hit": keyword,
    }


def extract_email_tree(root: Path, *, keyword: str | None = None) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    parser = BytesParser(policy=policy.default)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".eml":
            msg = parser.parsebytes(path.read_bytes())
            rec = _message_record(msg, str(path), keyword)
            if rec:
                hits.append(rec)
        elif suffix == ".mbox":
            box = mailbox.mbox(path)
            try:
                for i, msg in enumerate(box):
                    rec = _message_record(msg, f"{path}#{i}", keyword)
                    if rec:
                        hits.append(rec)
            finally:
                box.close()
    return hits
