"""LicenseSpend Explorer UI, Northwind sample pack, and enriched report payload."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

pytest.importorskip("duckdb")
pytest.importorskip("typer")
pytest.importorskip("jinja2")

from licensespend.constants import EXAMPLES, SAMPLE_AS_OF
from licensespend.privacy import contains_raw_email
from licensespend.report.explorer import (
    build_explorer_state,
    dispatch_licensespend,
    render_explorer_html,
    write_static,
)
from licensespend.report.service import build, build_payload, verify_watermark
from licensespend.usage.service import unused_seats

NORTHWIND = EXAMPLES / "northwind"


def test_northwind_unused_math() -> None:
    report = unused_seats(fixture_root=NORTHWIND, idle_days=90, as_of=date(2026, 9, 7))
    assert len([r for r in report.rows if r.sku == "m365-e5"]) == 4
    assert len([r for r in report.rows if r.sku == "slack-business-plus"]) == 3
    assert len([r for r in report.rows if r.sku == "github-team"]) == 2
    assert report.reclaim_monthly_aud == 281.0
    assert all(r.email is None for r in report.rows)


def test_acme_payload_still_127() -> None:
    payload = build_payload(client="acme", as_of=SAMPLE_AS_OF)
    assert payload.reclaim_monthly_aud == 127.0
    assert payload.reclaim_annual_aud == 1524.0
    assert payload.unused_count == 5
    assert payload.idle_buckets["90+"] >= 5
    assert payload.vendor_breakdown
    assert payload.department_breakdown
    assert payload.qbr_talk_track
    assert payload.watermark
    assert "Do not auto-revoke" in payload.disclaimer


def test_northwind_report_watermark(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LICENSESPEND_INCLUDE_EMAIL", "0")
    files = build(client="northwind", out_dir=tmp_path, as_of=SAMPLE_AS_OF)
    assert files.reclaim_monthly_aud == 281.0
    assert verify_watermark(Path(files.json_path))
    for path in (files.json_path, files.markdown_path, files.html_path):
        text = Path(path).read_text(encoding="utf-8")
        assert not contains_raw_email(text)
        assert "QBR talk-track" in text or path.endswith(".json")


def test_explorer_portfolio_and_client_switcher() -> None:
    state = build_explorer_state(as_of=SAMPLE_AS_OF)
    assert state["portfolio"]["reclaim_monthly_aud"] == 408.0
    assert state["portfolio"]["reclaim_annual_aud"] == 4896.0
    assert state["portfolio"]["unused_seats"] == 14
    assert set(state["clients"]) == {"acme", "northwind"}
    assert state["clients"]["acme"]["reclaim_monthly_aud"] == 127.0
    assert state["clients"]["northwind"]["reclaim_monthly_aud"] == 281.0
    html = render_explorer_html(state)
    assert "LicenseSpend Explorer" in html
    assert 'data-client="acme"' in html
    assert 'data-client="northwind"' in html
    assert "A$408.00" in html
    assert "searchParams.set" in html
    assert '.get("client")' in html
    assert not contains_raw_email(html)
    assert "@contoso.example" not in html
    assert "@northwind.example" not in html
    assert "Do not auto-revoke" in html


def test_dispatch_licensespend_html_and_api() -> None:
    html = dispatch_licensespend("GET", "/licensespend")
    assert html is not None
    assert html[0] == 200
    assert b"LicenseSpend Explorer" in html[2]
    api = dispatch_licensespend("GET", "/api/licensespend/status")
    assert api is not None
    assert b'"reclaim_monthly_aud": 408.0' in api[2]
    client = dispatch_licensespend("GET", "/api/licensespend/client", {"id": ["northwind"]})
    assert client is not None
    assert client[0] == 200
    assert b'"reclaim_monthly_aud": 281.0' in client[2]
    missing = dispatch_licensespend("GET", "/api/licensespend/client", {"id": ["unknown"]})
    assert missing is not None
    assert missing[0] == 404


def test_write_static_sample_packs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LICENSESPEND_INCLUDE_EMAIL", "0")
    result = write_static(tmp_path, as_of=SAMPLE_AS_OF)
    explorer = Path(result["explorer"])
    assert explorer.is_file()
    assert (tmp_path / "licensespend" / "acme-license-spend.html").is_file()
    assert (tmp_path / "licensespend" / "northwind-license-spend.json").is_file()
    assert result["portfolio"]["reclaim_monthly_aud"] == 408.0
    for path in tmp_path.rglob("*"):
        if path.suffix in {".html", ".md", ".json"}:
            assert not contains_raw_email(path.read_text(encoding="utf-8"))
