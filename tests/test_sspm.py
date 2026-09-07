"""SSPM integration tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_audit_inventory():
    from sspm.audit.service import inventory

    result = inventory(init_db=True)
    assert result["product"] == "sspm"
    assert result["tool_count"] >= 5
    assert (ROOT / "output" / "sspm" / "sspm-inventory.json").exists()


def test_m365_discovery():
    from sspm.m365_discovery.service import discover

    result = discover("contoso.onmicrosoft.com")
    assert result["tenant_type"] == "m365"
    assert "settings" in result


def test_oauth_grants():
    from sspm.oauth_grants.service import list_grants

    grants = list_grants("m365")
    assert len(grants) >= 1
    assert grants[0]["risk_level"] in ("low", "medium", "high")


def test_config_drift():
    from sspm.config_drift.service import diff

    drift = diff("m365")
    assert isinstance(drift, list)


def test_compliance_map():
    from sspm.compliance_map.service import map_framework

    refs = map_framework("cis-m365", "m365", [{"id": "1", "type": "mfa_enforced"}])
    assert len(refs) >= 1
    assert "control reference" in refs[0].get("note", "")


def test_report_no_forbidden_words():
    from sspm.report_writer.service import generate

    out = ROOT / "output" / "sspm" / "test_report.md"
    generate("m365", out)
    text = out.read_text(encoding="utf-8").lower()
    forbidden = {"compliance", "attestation", "certified", "guaranteed", "guarantees"}
    for word in forbidden:
        assert word not in re.findall(rf"\b{word}\b", text)
    assert "liability disclaimer" in text


def test_disclaimer_present():
    from sspm.disclaimers.service import load_disclaimer

    text = load_disclaimer("disclaimer_au")
    assert "NOT a security assessment" in text


def test_multi_tenant():
    from sspm.multi_tenant.service import add_tenant, list_tenants

    add_tenant("test-tenant", "m365", "client-123")
    tenants = list_tenants()
    assert any(t["name"] == "test-tenant" for t in tenants)


def test_loop_watch():
    from sspm.loop.watch import watch

    result = watch(fetch=False)
    assert "discoveries" in result
    assert "seen_count" in result


def test_web_app_import():
    from sspm.web.app import app

    assert app.title == "SSPM Configuration Report"


@pytest.mark.parametrize(
    "module",
    [
        "audit",
        "m365_discovery",
        "google_workspace_discovery",
        "github_discovery",
        "slack_discovery",
        "okta_discovery",
        "oauth_grants",
        "config_drift",
        "compliance_map",
        "report_writer",
        "multi_tenant",
        "disclaimers",
    ],
)
def test_module_imports(module: str):
    import importlib

    mod = importlib.import_module(f"sspm.{module}.service")
    assert mod is not None
