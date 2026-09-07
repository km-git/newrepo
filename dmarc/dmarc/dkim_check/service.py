"""DKIM record checker with public-key length validation."""

from __future__ import annotations

import base64
import re
from datetime import datetime, timezone

import dns.resolver
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from dmarc.db import clear_table, insert_rows
from dmarc.models import DkimFinding


def _fetch_dkim(domain: str, selector: str) -> str | None:
    name = f"{selector}._domainkey.{domain}"
    try:
        answers = dns.resolver.resolve(name, "TXT")
    except Exception:
        return None
    parts = []
    for rr in answers:
        parts.append(rr.to_text().strip('"'))
    return "".join(parts) if parts else None


def _public_key_bits(record: str) -> int | None:
    match = re.search(r"p=([A-Za-z0-9+/=]+)", record)
    if not match:
        return None
    raw = match.group(1)
    try:
        key_bytes = base64.b64decode(raw + "=" * (-len(raw) % 4))
        pub = serialization.load_der_public_key(key_bytes, backend=default_backend())
        numbers = pub.public_numbers()
        return numbers.n.bit_length()
    except Exception:
        return None


def check_dkim(domain: str, selector: str, *, replace: bool = False) -> DkimFinding:
    record = _fetch_dkim(domain, selector) or ""
    bits = _public_key_bits(record) if record else None
    warnings: list[str] = []
    if not record:
        warnings.append(f"no DKIM record at selector {selector}")
    elif bits is not None:
        if bits < 1024:
            warnings.append(f"RSA key {bits} bits (<1024 warning threshold)")
        elif bits < 2048:
            warnings.append(f"RSA key {bits} bits (<2048 advisory threshold)")

    finding = DkimFinding(
        domain=domain,
        selector=selector,
        record=record,
        public_key_length=bits,
        warnings=warnings,
    )
    if replace:
        clear_table("findings_dkim")
    row = finding.model_dump(mode="json")
    row["checked_at"] = datetime.now(timezone.utc).isoformat()
    insert_rows("findings_dkim", [row])
    return finding


def check_all_selectors(domain: str, selectors: list[str]) -> list[DkimFinding]:
    clear_table("findings_dkim")
    return [check_dkim(domain, sel, replace=False) for sel in selectors]
