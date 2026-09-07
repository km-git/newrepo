"""Tests for DMARC deliverability monitor."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dmarc_db(tmp_path, monkeypatch):
    db = tmp_path / "test.duckdb"
    out = tmp_path / "output"
    reports = tmp_path / "reports"
    monkeypatch.setenv("DMARC_DB_PATH", str(db))
    monkeypatch.setenv("DMARC_DATA_DIR", str(out))
    monkeypatch.setenv("DMARC_REPORTS_DIR", str(reports))
    yield db


def test_spf_parse_counts_lookups(dmarc_db):
    from dmarc.spf_parser.service import parse_spf

    record = 'v=spf1 include:_spf.google.com include:mail.example.com ~all'
    with patch("dmarc.spf_parser.service._fetch_spf", return_value=record):
        finding = parse_spf("example.com.au")
    assert finding.dns_lookup_count == 2
    assert finding.all_qualifier == "~"
    assert "more than 10 DNS lookups" not in finding.warnings


def test_spf_warns_on_lookup_limit(dmarc_db):
    from dmarc.spf_parser.service import parse_spf

    mechs = " ".join(["include:sp%d.example.com" % i for i in range(12)])
    record = f"v=spf1 {mechs} -all"
    with patch("dmarc.spf_parser.service._fetch_spf", return_value=record):
        finding = parse_spf("example.com.au")
    assert finding.dns_lookup_count > 10
    assert any("10 DNS lookups" in w for w in finding.warnings)


def test_dkim_key_length_parsing(dmarc_db):
    from dmarc.dkim_check.service import _public_key_bits

    # Minimal invalid record should not crash
    assert _public_key_bits("v=DKIM1; k=rsa; p=abc") is None


def test_ingest_sample_rua(dmarc_db):
    from dmarc.dmarc_ingest.service import ingest_reports

    findings = ingest_reports("example.com.au", demo=True)
    assert len(findings) >= 2
    assert findings[0].domain == "example.com.au"


def test_report_has_disclaimer(dmarc_db):
    from dmarc.dmarc_ingest.service import ingest_reports
    from dmarc.report_writer.service import generate_report

    ingest_reports("example.com.au", demo=True)
    md, js = generate_report("example.com.au")
    text = md.read_text(encoding="utf-8")
    assert "Email Deliverability & Brand-Protection Review" in text
    assert "Liability disclaimer" in text
    assert "compliance" not in text.lower() or "deliverability observation" in text.lower()
    payload = json.loads(js.read_text(encoding="utf-8"))
    assert payload["title"] == "Email Deliverability & Brand-Protection Review"


def test_web_health(dmarc_db):
    from dmarc.web.app import app

    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_loop_classify_dmarc_context():
    from dmarc.loop.watch import classify

    result = classify(
        {
            "title": "parsedmarc 8.6.4 release with DMARC aggregate parser",
            "summary": "MIT licensed dnspython integration",
            "module_hint": "dmarc_ingest",
        }
    )
    assert result["verdict"] in {"discover", "watch"}
    assert result["module"] != "unknown"


def test_audit_inventory_writes_json(dmarc_db, tmp_path, monkeypatch):
    from dmarc.audit.service import build_inventory

    monkeypatch.chdir(tmp_path)
    (tmp_path / "disclaimers").mkdir()
    inv = build_inventory()
    assert "tools" in inv
    assert len(inv["tools"]) >= 5
