"""Shared DNS memory resolver for module tests."""

from __future__ import annotations

from dmarc.dns_resolver import MemoryResolver


def example_resolver() -> MemoryResolver:
    resolver = MemoryResolver()
    domain = "example.com.au"
    resolver.add(domain, "A", "93.184.216.34", ttl=300)
    resolver.add(domain, "AAAA", "2606:2800:220:1:248:1893:25c8:1946", ttl=300)
    resolver.add(domain, "MX", "10 mail.example.com.au", ttl=300)
    resolver.add(
        domain,
        "TXT",
        "v=spf1 include:_spf.google.com include:mailgun.org -all",
        ttl=300,
    )
    resolver.add("_spf.google.com", "TXT", "v=spf1 ip4:35.190.247.0/24 ~all", ttl=300)
    resolver.add("mailgun.org", "TXT", "v=spf1 ip4:69.45.24.0/24 -all", ttl=300)
    resolver.add("_dmarc.example.com.au", "TXT", "v=DMARC1; p=none; rua=mailto:dmarc@example.com.au", ttl=300)
    resolver.add("_mta-sts.example.com.au", "TXT", "v=STSv1; id=20260907", ttl=300)
    resolver.add("_smtp._tls.example.com.au", "TXT", "v=TLSRPTv1; rua=mailto:tlsrpt@example.com.au", ttl=300)
    resolver.add("default._bimi.example.com.au", "TXT", "v=BIMI1; l=https://example.com.au/bimi.svg", ttl=300)
    return resolver
