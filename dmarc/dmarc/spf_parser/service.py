"""SPF record parser with RFC 7208 lookup counting."""

from __future__ import annotations

from datetime import datetime, timezone

import dns.resolver

from dmarc.db import clear_table, insert_rows
from dmarc.models import SpfFinding

LOOKUP_MECHANISMS = frozenset({"include", "a", "mx", "ptr", "exists", "redirect"})


def _fetch_spf(domain: str) -> str | None:
    try:
        answers = dns.resolver.resolve(domain, "TXT")
    except Exception:
        return None
    for rr in answers:
        txt = rr.to_text().strip('"')
        if txt.lower().startswith("v=spf1"):
            return txt
    return None


def _split_mechanisms(record: str) -> list[str]:
    return record.split()[1:] if record else []


def _count_dns_lookups(mechanisms: list[str]) -> int:
    count = 0
    for mech in mechanisms:
        token = mech.split(":", 1)[0].split("/", 1)[0].lower()
        if token in LOOKUP_MECHANISMS or token == "redirect":
            count += 1
    return count


def _all_qualifier(record: str) -> str:
    for mech in _split_mechanisms(record):
        if mech.endswith("all") or mech == "all":
            if mech.startswith(("+", "~", "-", "?")):
                return mech[0]
            return "+"
    return "?"


def parse_spf(domain: str) -> SpfFinding:
    record = _fetch_spf(domain) or ""
    mechanisms = _split_mechanisms(record)
    lookup_count = _count_dns_lookups(mechanisms)
    qualifier = _all_qualifier(record)
    warnings: list[str] = []
    if not record:
        warnings.append("missing SPF TXT record")
    if lookup_count > 10:
        warnings.append("more than 10 DNS lookups")
    if qualifier == "?":
        warnings.append("missing `all` mechanism")
    if qualifier == "+":
        warnings.append("`+all` is too permissive")

    finding = SpfFinding(
        domain=domain,
        record=record,
        dns_lookup_count=lookup_count,
        lookups=mechanisms,
        all_qualifier=qualifier,
        warnings=warnings,
    )
    clear_table("findings_spf")
    row = finding.model_dump(mode="json")
    row["checked_at"] = datetime.now(timezone.utc).isoformat()
    insert_rows("findings_spf", [row])
    return finding
