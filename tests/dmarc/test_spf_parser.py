from __future__ import annotations

from dmarc.dns_resolver import MemoryResolver
from dmarc.spf_parser.service import parse_domain, parse_record
from tests.dmarc.helpers import example_resolver


def test_spf_counts_includes_and_flags_plus_all() -> None:
    finding = parse_record("example.com.au", "v=spf1 include:_spf.google.com +all", example_resolver())
    assert finding.dns_lookup_count >= 1
    assert finding.all_qualifier == "+"
    assert any("`+all` is too permissive" in w for w in finding.warnings)


def test_spf_ten_lookup_budget() -> None:
    resolver = MemoryResolver()
    includes = " ".join(f"include:n{i}.example" for i in range(11))
    for i in range(11):
        resolver.add(f"n{i}.example", "TXT", "v=spf1 ip4:1.2.3.4 -all")
    finding = parse_record("example.com.au", f"v=spf1 {includes} -all", resolver)
    assert finding.dns_lookup_count > 10
    assert any("more than 10 DNS lookups" in w for w in finding.warnings)


def test_spf_parse_domain_persists(tmp_path) -> None:
    payload = parse_domain("example.com.au", resolver=example_resolver(), root=tmp_path)
    assert payload["all_qualifier"] == "-"
    assert payload["dns_lookup_count"] >= 2
