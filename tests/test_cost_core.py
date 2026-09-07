"""End-to-end module smoke tests with fixtures."""

from pathlib import Path

import pytest

from cost.audit.service import inventory
from cost.aws_inventory.service import scan_aws
from cost.azure_inventory.service import scan_azure
from cost.compliance_map.service import map_findings
from cost.config_drift.service import diff
from cost.cost_explorer.service import explore
from cost.db.store import FindingsStore
from cost.gcp_inventory.service import scan_gcp
from cost.multi_account.service import run_accounts
from cost.report_writer.service import generate
from cost.rightsizing.service import scan as rightsizing_scan
from cost.untagged.service import scan as untagged_scan


@pytest.fixture()
def store(tmp_path, monkeypatch):
    db = tmp_path / "cost.sqlite"
    monkeypatch.setenv("COST_DB", str(db))
    return FindingsStore(db)


def test_audit_inventory_writes_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = inventory()
    assert payload["product"] == "cost"
    assert payload["tool_count"] >= 8


def test_full_pipeline(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COST_DB", str(store.path))
    scan_aws(store=store)
    scan_azure(store=store)
    scan_gcp(store=store)
    explore(store=store)
    rightsizing_scan(store=store)
    untagged_scan(store=store)
    diff(store=store)
    map_findings(store=store)
    run_accounts()
    report = generate(store=store, output=tmp_path / "report.md")
    assert Path(report["markdown_path"]).exists()
    text = Path(report["markdown_path"]).read_text(encoding="utf-8").lower()
    forbidden = ("compliance", "attestation", "certified", "guaranteed", "guarantees")
    for word in forbidden:
        assert word not in text
    assert "cloud cost & configuration review" in text
