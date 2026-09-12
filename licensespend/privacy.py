"""Hash emails with a per-tenant salt before they hit DuckDB or HTML."""

from __future__ import annotations

import hashlib
import re

from licensespend.constants import tenant_salt

_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


def hash_email(email: str, *, salt: str | None = None) -> str:
    value = (email or "").strip().lower()
    if not value:
        return ""
    material = f"{salt or tenant_salt()}:{value}".encode()
    return hashlib.sha256(material).hexdigest()


def contains_raw_email(text: str) -> bool:
    return bool(_EMAIL_RE.search(text or ""))


def redact_emails(text: str, *, salt: str | None = None) -> str:
    def _sub(match: re.Match[str]) -> str:
        return hash_email(match.group(0), salt=salt)

    return _EMAIL_RE.sub(_sub, text or "")
