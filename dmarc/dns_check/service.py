"""Check A, AAAA, MX, SPF TXT, DKIM, DMARC, MTA-STS, TLS-RPT, BIMI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dmarc.config import dkim_selectors
from dmarc.dns_check.models import DnsFinding
from dmarc.dns_resolver import Resolver, default_resolver
from dmarc.store import insert_rows, utcnow


def _txt_values(resolver: Resolver, name: str) -> list[tuple[str, int | None]]:
    return [(row.value, row.ttl) for row in resolver.lookup(name, "TXT")]


def check_domain(
    domain: str,
    resolver: Resolver | None = None,
    selectors: list[str] | None = None,
    root: Path | None = None,
    persist: bool = True,
) -> list[dict[str, Any]]:
    domain = domain.strip().lower().rstrip(".")
    resolver = resolver or default_resolver()
    stamp = utcnow()
    findings: list[DnsFinding] = []

    for rdtype in ("A", "AAAA", "MX", "CNAME"):
        for answer in resolver.lookup(domain, rdtype):
            findings.append(
                DnsFinding(
                    domain=domain,
                    record_type=rdtype,
                    value=answer.value,
                    ttl=answer.ttl,
                    last_checked_at=stamp,
                )
            )

    for value, ttl in _txt_values(resolver, domain):
        rtype = "SPF" if value.lower().startswith("v=spf1") else "TXT"
        findings.append(DnsFinding(domain=domain, record_type=rtype, value=value, ttl=ttl, last_checked_at=stamp))

    for label, template in (
        ("DMARC", f"_dmarc.{domain}"),
        ("MTA-STS", f"_mta-sts.{domain}"),
        ("TLS-RPT", f"_smtp._tls.{domain}"),
        ("BIMI", f"default._bimi.{domain}"),
    ):
        rows = _txt_values(resolver, template)
        if not rows:
            findings.append(DnsFinding(domain=domain, record_type=label, value="", ttl=None, last_checked_at=stamp))
        for value, ttl in rows:
            findings.append(DnsFinding(domain=domain, record_type=label, value=value, ttl=ttl, last_checked_at=stamp))

    for selector in selectors or dkim_selectors():
        name = f"{selector}._domainkey.{domain}"
        rows = _txt_values(resolver, name)
        for value, ttl in rows:
            findings.append(
                DnsFinding(
                    domain=domain,
                    record_type="DKIM",
                    value=f"{selector} {value}",
                    ttl=ttl,
                    last_checked_at=stamp,
                )
            )

    payload = [row.model_dump() for row in findings]
    if persist:
        insert_rows("findings_dns", payload, root)
    return payload
