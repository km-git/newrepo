"""DNS record checker for customer domains."""

from __future__ import annotations

from datetime import datetime, timezone

import dns.exception
import dns.resolver

from dmarc.config import DEFAULT_DKIM_SELECTORS
from dmarc.db import clear_table, insert_rows
from dmarc.models import DnsFinding

RESOLVER = dns.resolver.Resolver()
RESOLVER.lifetime = 10.0


def _query(name: str, rtype: str) -> list[tuple[str, int | None]]:
    try:
        answers = RESOLVER.resolve(name, rtype)
        return [(rr.to_text(), answers.rrset.ttl if answers.rrset else None) for rr in answers]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
        return []


def check_domain(domain: str, dkim_selectors: tuple[str, ...] = DEFAULT_DKIM_SELECTORS) -> list[DnsFinding]:
    now = datetime.now(timezone.utc)
    findings: list[DnsFinding] = []

    for rtype in ("A", "AAAA", "MX", "TXT", "CNAME"):
        for value, ttl in _query(domain, rtype):
            findings.append(
                DnsFinding(
                    domain=domain,
                    record_type=rtype,
                    value=value,
                    ttl=ttl,
                    last_checked_at=now,
                )
            )

    special = [
        ("TXT", f"_dmarc.{domain}"),
        ("TXT", f"_mta-sts.{domain}"),
        ("TXT", f"_smtp._tls.{domain}"),
        ("TXT", f"default._bimi.{domain}"),
    ]
    for rtype, name in special:
        for value, ttl in _query(name, rtype):
            findings.append(
                DnsFinding(domain=domain, record_type=f"{rtype}@{name}", value=value, ttl=ttl, last_checked_at=now)
            )

    for selector in dkim_selectors:
        name = f"{selector}._domainkey.{domain}"
        for value, ttl in _query(name, "TXT"):
            findings.append(
                DnsFinding(
                    domain=domain,
                    record_type=f"DKIM@{selector}",
                    value=value,
                    ttl=ttl,
                    last_checked_at=now,
                )
            )

    clear_table("findings_dns")
    rows = [f.model_dump(mode="json") for f in findings]
    insert_rows("findings_dns", rows)
    return findings
