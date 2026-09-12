from __future__ import annotations

from dmarc.forensic_report.service import list_forensic, mask_email, parse_ruf_xml
from dmarc.inbox_placement.service import provider_for, run_test


def test_mask_email_hides_local_part() -> None:
    masked = mask_email("customer.jane@example.net")
    assert "customer.jane" not in masked
    assert masked.endswith("@example.net") or "***" in masked


def test_ruf_parse_and_empty_ok(tmp_path) -> None:
    xml = """<?xml version="1.0"?><feedback><incident>
      <domain>example.com.au</domain>
      <source><ip_address>203.0.113.9</ip_address></source>
      <envelope_from>victim@example.net</envelope_from>
      <subject>Hello</subject><dkim>fail</dkim><spf>fail</spf>
    </incident></feedback>"""
    rows = parse_ruf_xml(xml)
    assert len(rows) == 1
    assert rows[0].source_ip == "203.0.113.9"
    assert "victim@" not in rows[0].from_address
    listed = list_forensic(root=tmp_path)
    assert isinstance(listed, list)


def test_list_forensic_does_not_duplicate_on_repeat(tmp_path) -> None:
    first = list_forensic(root=tmp_path)
    second = list_forensic(root=tmp_path)
    assert len(first) == len(second)
    assert first
    from dmarc.forensic_report.service import ingest_ruf_fixtures

    ingest_ruf_fixtures(root=tmp_path)
    third = list_forensic(root=tmp_path)
    assert len(third) == len(first)


def test_inbox_dry_run_seeds(tmp_path) -> None:
    rows = run_test(
        "noreply@example.com.au",
        ["seed1@gmail.com", "seed2@outlook.com", "seed3@yahoo.com"],
        dry_run=True,
        root=tmp_path,
    )
    assert {r["provider"] for r in rows} >= {"Gmail", "Outlook", "Yahoo"}
    assert all(r["placement"] == "missing" for r in rows)
    assert provider_for("a@icloud.com") == "iCloud"


def test_smtp_starttls_uses_ssl_context(monkeypatch, tmp_path) -> None:
    import ssl

    seen: dict = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=20):
            seen["host"] = host

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self, context=None):
            seen["context"] = context

        def login(self, *args):
            return None

        def send_message(self, *_args):
            return None

    monkeypatch.setenv("DMARC_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("DMARC_SMTP_PORT", "587")
    monkeypatch.setattr("dmarc.inbox_placement.service.smtplib.SMTP", FakeSMTP)
    run_test("noreply@example.com.au", ["seed1@gmail.com"], dry_run=False, root=tmp_path)
    assert isinstance(seen.get("context"), ssl.SSLContext)
