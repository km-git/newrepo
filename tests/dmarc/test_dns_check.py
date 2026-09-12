from __future__ import annotations

from dmarc.dns_check.service import check_domain
from tests.dmarc.helpers import example_resolver


def test_dns_check_covers_auth_records(tmp_path) -> None:
    rows = check_domain("example.com.au", resolver=example_resolver(), root=tmp_path)
    types = {r["record_type"] for r in rows}
    assert {"A", "AAAA", "MX", "SPF", "DMARC", "MTA-STS", "TLS-RPT", "BIMI"} <= types
    dmarc = next(r for r in rows if r["record_type"] == "DMARC")
    assert "v=DMARC1" in dmarc["value"]
    assert "p=none" in dmarc["value"]
