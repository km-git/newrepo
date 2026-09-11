"""SPF RFC 7208 parser with the 10-DNS-lookup budget."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dmarc.dns_resolver import Resolver, default_resolver
from dmarc.spf_parser.models import SpfFinding
from dmarc.store import insert_rows, utcnow

LOOKUP_MECHS = ("include", "a", "mx", "ptr", "exists")
LOOKUP_MODS = ("redirect",)
MAX_LOOKUPS = 10
TOKEN_RE = re.compile(r"^(?P<qual>[+~?\-]?)(?P<mech>[a-z0-9]+)(?::(?P<arg>.+))?$", re.I)


def _spf_from_txt(values: list[str]) -> str:
    for value in values:
        if value.lower().startswith("v=spf1"):
            return value
    return ""


def _qualifier(token: str) -> str:
    if token[:1] in "+~?-":
        return token[:1]
    return "+"


def parse_record(
    domain: str,
    record: str,
    resolver: Resolver | None = None,
    remaining: int | None = None,
    seen: set[str] | None = None,
) -> SpfFinding:
    """Parse one SPF string and recursively count DNS-causing mechanisms."""
    resolver = resolver or default_resolver()
    remaining = MAX_LOOKUPS if remaining is None else remaining
    seen = seen if seen is not None else set()
    lookups: list[str] = []
    warnings: list[str] = []
    all_qualifier = ""
    used = 0

    tokens = record.split()
    if not tokens or tokens[0].lower() != "v=spf1":
        warnings.append("not an SPF record")
        return SpfFinding(domain=domain, record=record, dns_lookup_count=0, warnings=warnings)

    for raw in tokens[1:]:
        match = TOKEN_RE.match(raw)
        if not match:
            continue
        mech = match.group("mech").lower()
        arg = match.group("arg") or ""
        qual = match.group("qual") or "+"
        if mech == "all":
            all_qualifier = qual if qual else "+"
            continue
        if mech in ("ip4", "ip6", "exp"):
            continue
        if mech in LOOKUP_MECHS or mech in LOOKUP_MODS:
            used += 1
            target = arg or domain
            lookups.append(f"{mech}:{target}")
            if mech == "include" and arg and arg not in seen:
                seen.add(arg)
                nested_txt = [row.value for row in resolver.lookup(arg, "TXT")]
                nested_record = _spf_from_txt(nested_txt)
                if nested_record:
                    nested = parse_record(arg, nested_record, resolver, remaining=remaining - used, seen=seen)
                    used += nested.dns_lookup_count
                    lookups.extend(nested.lookups)
                    warnings.extend(nested.warnings)
            if mech == "redirect" and arg and arg not in seen:
                seen.add(arg)
                nested_txt = [row.value for row in resolver.lookup(arg, "TXT")]
                nested_record = _spf_from_txt(nested_txt)
                if nested_record:
                    nested = parse_record(arg, nested_record, resolver, remaining=remaining - used, seen=seen)
                    used += nested.dns_lookup_count
                    lookups.extend(nested.lookups)
                    warnings.extend(nested.warnings)
                    if not all_qualifier:
                        all_qualifier = nested.all_qualifier

    if used > MAX_LOOKUPS:
        warnings.append("more than 10 DNS lookups")
    if not all_qualifier:
        warnings.append("missing `all`")
    if all_qualifier == "+":
        warnings.append("`+all` is too permissive")
    return SpfFinding(
        domain=domain,
        record=record,
        dns_lookup_count=used,
        lookups=lookups,
        all_qualifier=all_qualifier,
        warnings=warnings,
        last_checked_at=utcnow(),
    )


def parse_domain(
    domain: str,
    resolver: Resolver | None = None,
    root: Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    resolver = resolver or default_resolver()
    domain = domain.strip().lower().rstrip(".")
    record = _spf_from_txt([row.value for row in resolver.lookup(domain, "TXT")])
    finding = (
        parse_record(domain, record, resolver)
        if record
        else SpfFinding(
            domain=domain,
            record="",
            dns_lookup_count=0,
            warnings=["no SPF TXT record"],
            last_checked_at=utcnow(),
        )
    )
    payload = finding.model_dump()
    stored = {
        **payload,
        "lookups": ",".join(finding.lookups),
        "warnings": "; ".join(finding.warnings),
    }
    if persist:
        insert_rows("findings_spf", [stored], root)
    return payload
