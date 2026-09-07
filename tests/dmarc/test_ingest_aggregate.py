from __future__ import annotations

from pathlib import Path

from dmarc.aggregate_report.service import run_report
from dmarc.dmarc_ingest.service import ingest_fixtures, parse_aggregate_xml
from dmarc.paths import RUA_FIXTURES


def test_fixtures_cover_ten_rua_reports() -> None:
    files = list(RUA_FIXTURES.glob("*.xml"))
    assert len(files) >= 10


def test_ingest_fixtures_and_aggregate(tmp_path: Path) -> None:
    rows = ingest_fixtures(root=tmp_path)
    assert len(rows) >= 10
    assert {r["source_org"] for r in rows} >= {"google.com", "microsoft.com"}
    summary = run_report(domain="example.com.au", since="3650d", root=tmp_path)
    assert summary["message_count"] > 0
    assert Path(summary["html"]).exists()
    assert 0 <= summary["pass_rate"] <= 1
    assert summary["reject_ready"] is False or summary["pass_rate"] >= 0.99


def test_parse_inline_xml() -> None:
    xml = """<?xml version="1.0"?><feedback>
      <report_metadata><org_name>t</org_name>
        <date_range><begin>1</begin><end>2</end></date_range></report_metadata>
      <policy_published><domain>example.com.au</domain></policy_published>
      <record><row><source_ip>1.2.3.4</source_ip><count>3</count>
        <policy_evaluated><disposition>none</disposition><dkim>pass</dkim><spf>pass</spf>
        </policy_evaluated></row>
        <identifiers><header_from>example.com.au</header_from></identifiers>
      </record></feedback>"""
    rows = parse_aggregate_xml(xml)
    assert rows[0].count == 3
    assert rows[0].dkim_result == "pass"


def test_imap_uses_default_ssl_context(monkeypatch, tmp_path: Path) -> None:
    import ssl

    from dmarc.dmarc_ingest.service import ingest_imap

    seen: dict = {}

    class FakeIMAP:
        def __init__(self, host, ssl_context=None, **kwargs):
            seen["host"] = host
            seen["ssl_context"] = ssl_context

        def login(self, *_args):
            return "OK"

        def select(self, *_args):
            return "OK"

        def search(self, *_args):
            return "OK", [b""]

        def logout(self):
            return "OK"

    monkeypatch.setattr("dmarc.dmarc_ingest.service.imaplib.IMAP4_SSL", FakeIMAP)
    monkeypatch.setenv("DMARC_IMAP_PASS", "unit-test-secret")
    ingest_imap("imap.example.com", "user", root=tmp_path)
    assert seen["host"] == "imap.example.com"
    assert isinstance(seen["ssl_context"], ssl.SSLContext)
    assert seen["ssl_context"].check_hostname is True
