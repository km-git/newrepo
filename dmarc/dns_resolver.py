"""DNS lookups: dnspython first, then Cloudflare DNS-over-HTTPS, then socket."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx

try:
    import dns.exception
    import dns.resolver
except ImportError:  # pragma: no cover - optional extra
    dns = None  # type: ignore[assignment]


class Resolver(Protocol):
    def lookup(self, name: str, rdtype: str) -> list[DnsAnswer]: ...


@dataclass
class DnsAnswer:
    name: str
    rdtype: str
    value: str
    ttl: int | None = None


@dataclass
class MemoryResolver:
    """Injectable records for tests and offline demos."""

    records: dict[tuple[str, str], list[DnsAnswer]] = field(default_factory=dict)

    def add(self, name: str, rdtype: str, value: str, ttl: int = 300) -> None:
        key = (name.lower().rstrip("."), rdtype.upper())
        self.records.setdefault(key, []).append(DnsAnswer(name=key[0], rdtype=key[1], value=value, ttl=ttl))

    def lookup(self, name: str, rdtype: str) -> list[DnsAnswer]:
        key = (name.lower().rstrip("."), rdtype.upper())
        return list(self.records.get(key, []))


class LiveResolver:
    def lookup(self, name: str, rdtype: str) -> list[DnsAnswer]:
        rdtype = rdtype.upper()
        name = name.rstrip(".")
        answers = self._dnspython(name, rdtype)
        if answers is not None:
            return answers
        return self._doh(name, rdtype)

    def _dnspython(self, name: str, rdtype: str) -> list[DnsAnswer] | None:
        if dns is None:
            return None
        try:
            resolved = dns.resolver.resolve(name, rdtype, lifetime=5)
        except (dns.exception.DNSException, OSError):
            return []
        out: list[DnsAnswer] = []
        ttl = int(getattr(resolved, "ttl", 0) or 0) or None
        for item in resolved:
            if rdtype == "MX":
                value = f"{int(item.preference)} {str(item.exchange).rstrip('.')}"
            elif rdtype == "TXT":
                if hasattr(item, "strings"):
                    value = "".join(
                        part.decode("utf-8", "replace") if isinstance(part, bytes) else str(part)
                        for part in item.strings
                    )
                else:
                    value = str(item).strip('"')
            else:
                value = str(item).rstrip(".")
            out.append(DnsAnswer(name=name, rdtype=rdtype, value=value, ttl=ttl))
        return out

    def _doh(self, name: str, rdtype: str) -> list[DnsAnswer]:
        try:
            response = httpx.get(
                "https://cloudflare-dns.com/dns-query",
                params={"name": name, "type": rdtype},
                headers={"accept": "application/dns-json"},
                timeout=8.0,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, OSError):
            return []
        out: list[DnsAnswer] = []
        for answer in payload.get("Answer") or []:
            data = str(answer.get("data") or "").strip().strip('"')
            ttl = int(answer.get("TTL") or 0) or None
            if rdtype == "TXT":
                data = data.replace('" "', "").strip('"')
            out.append(DnsAnswer(name=name, rdtype=rdtype, value=data, ttl=ttl))
        return out


def default_resolver() -> Resolver:
    return LiveResolver()
