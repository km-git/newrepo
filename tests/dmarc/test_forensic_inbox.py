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
    assert rows[0].source_ip == "203.0.113.9"
    assert "victim@" not in rows[0].from_address
    listed = list_forensic(root=tmp_path)
    assert isinstance(listed, list)


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
