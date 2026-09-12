"""DKIM TXT checker + RSA public-key length."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from dmarc.config import dkim_selectors
from dmarc.dkim_check.models import DkimFinding
from dmarc.dns_resolver import Resolver, default_resolver
from dmarc.store import insert_rows, utcnow

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import load_der_public_key
except ImportError:  # pragma: no cover
    rsa = None  # type: ignore[assignment]
    load_der_public_key = None  # type: ignore[assignment]


def parse_dkim_tags(record: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for part in record.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        tags[key.strip().lower()] = value.strip()
    return tags


def public_key_bits(p_b64: str) -> int | None:
    if not p_b64 or load_der_public_key is None:
        return None
    padded = p_b64 + "=" * (-len(p_b64) % 4)
    try:
        der = base64.b64decode(padded)
        key = load_der_public_key(der)
    except (ValueError, TypeError):
        return None
    if rsa is not None and isinstance(key, rsa.RSAPublicKey):
        return int(key.key_size)
    numbers = getattr(key, "key_size", None)
    return int(numbers) if numbers else None


def check_selector(
    domain: str,
    selector: str,
    resolver: Resolver | None = None,
) -> DkimFinding:
    resolver = resolver or default_resolver()
    domain = domain.strip().lower().rstrip(".")
    name = f"{selector}._domainkey.{domain}"
    rows = resolver.lookup(name, "TXT")
    record = rows[0].value if rows else ""
    warnings: list[str] = []
    bits = None
    if not record:
        warnings.append(f"no DKIM TXT at {name}")
    else:
        tags = parse_dkim_tags(record)
        bits = public_key_bits(tags.get("p", ""))
        if bits is None:
            warnings.append("could not parse DKIM public key")
        elif bits < 1024:
            warnings.append("RSA key shorter than 1024 bits")
        elif bits < 2048:
            warnings.append("RSA key shorter than 2048 bits (advisory)")
        if tags.get("k", "rsa").lower() not in {"rsa", ""}:
            warnings.append(f"key type {tags.get('k')} is not RSA")
    return DkimFinding(
        domain=domain,
        selector=selector,
        record=record,
        public_key_length=bits,
        warnings=warnings,
        last_checked_at=utcnow(),
    )


def check_domain(
    domain: str,
    selector: str | None = None,
    resolver: Resolver | None = None,
    root: Path | None = None,
    persist: bool = True,
) -> list[dict[str, Any]]:
    names = [selector] if selector else dkim_selectors()
    findings = [check_selector(domain, name, resolver) for name in names]
    # Keep rows that resolved, plus explicit selector checks even if empty.
    kept = findings if selector else [row for row in findings if row.record] or findings[:1]
    payload = [row.model_dump() for row in kept]
    stored = [{**row, "warnings": "; ".join(row["warnings"])} for row in payload]
    if persist:
        insert_rows("findings_dkim", stored, root)
    return payload
