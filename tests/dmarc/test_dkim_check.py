from __future__ import annotations

import base64

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from dmarc.dkim_check.service import check_selector, parse_dkim_tags, public_key_bits
from dmarc.dns_resolver import MemoryResolver


def _rsa_txt(bits: int = 2048) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    der = key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    return "v=DKIM1; k=rsa; p=" + base64.b64encode(der).decode("ascii")


def test_parse_tags_and_key_length() -> None:
    record = _rsa_txt(2048)
    tags = parse_dkim_tags(record)
    assert tags["k"] == "rsa"
    bits = public_key_bits(tags["p"])
    assert bits == 2048


def test_short_key_warning() -> None:
    resolver = MemoryResolver()
    resolver.add("google._domainkey.example.com.au", "TXT", _rsa_txt(1024))
    finding = check_selector("example.com.au", "google", resolver)
    assert finding.public_key_length == 1024
    assert any("2048" in w for w in finding.warnings)
