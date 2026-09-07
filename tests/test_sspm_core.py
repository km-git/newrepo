"""SSPM core module behaviour on fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from sspm.audit.service import inventory
from sspm.compliance_map.service import map_tenant
from sspm.config_drift.service import diff_tenant
from sspm.constants import PRESIDIO_SOURCE
from sspm.db.store import FindingsStore
from sspm.discovery import load_fixture
from sspm.github_discovery.service import discover_github
from sspm.google_workspace_discovery.service import discover_gws
from sspm.m365_discovery.service import discover_m365
from sspm.multi_tenant.service import add_tenant, list_tenants
from sspm.oauth_grants.service import list_grants, risk_for_scopes
from sspm.okta_discovery.service import discover_okta
from sspm.slack_discovery.service import discover_slack


def test_inventory_writes_and_inits_db(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "sspm.sqlite"
    monkeypatch.setenv("SSPM_DB", str(db))
    monkeypatch.chdir(tmp_path)
    payload = inventory(init_db=True, write=True)
    assert payload["tool_count"] >= 10
    assert payload["gates"]["no_trivy"] is True
    assert payload["gates"]["no_steampipe"] is True
    assert PRESIDIO_SOURCE in payload["gates"]["presidio_source"]
    assert Path(payload["written"]).is_file()
    store = FindingsStore(db)
    assert store.fetchall("tenants") == []


def test_five_discoveries_persist(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "sspm.sqlite"
    monkeypatch.setenv("SSPM_DB", str(db))
    store = FindingsStore(db)
    m365 = discover_m365(store=store)
    gws = discover_gws(store=store)
    gh = discover_github(store=store)
    slack = discover_slack(store=store)
    okta = discover_okta(store=store)
    assert m365["tenant_type"] == "m365"
    assert gws["settings"]
    assert gh["honest_gap"]
    assert "message" not in slack["honest_gap"].lower() or "not scanned" in slack["honest_gap"].lower()
    assert okta["apps"]
    tenants = store.fetchall("findings_tenants")
    assert len(tenants) == 5
    settings = store.fetchall("findings_settings")
    assert len(settings) >= 20


def test_oauth_and_drift_and_control_refs(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "sspm.sqlite"
    monkeypatch.setenv("SSPM_DB", str(db))
    store = FindingsStore(db)
    grants = list_grants(tenant="m365", store=store)
    assert grants
    assert any(g.risk_level == "high" for g in grants)
    assert risk_for_scopes("User.Read") == "low"
    drift = diff_tenant(tenant="m365", store=store)
    assert drift
    assert any(d.setting_name == "userConsent.allowed" for d in drift)
    refs = map_tenant(framework="cis-m365", tenant="m365", store=store)
    assert refs
    assert all("compliance" not in r.title.lower() for r in refs)
    assert store.fetchall("findings_oauth")
    assert store.fetchall("findings_drift")
    assert store.fetchall("findings_compliance")


def test_tenant_registry(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    add_tenant(name="acme", tenant_type="m365", client_id="abc")
    rows = list_tenants()
    assert rows[0].name == "acme"
    assert rows[0].cron_expr == "0 9 * * 1"
    assert (tmp_path / "output/sspm/tenants.yaml").is_file()


def test_load_fixture_rejects_unknown_tenant() -> None:
    with pytest.raises(ValueError, match="unknown tenant"):
        load_fixture("../etc/passwd")
    with pytest.raises(ValueError, match="unknown tenant"):
        load_fixture("m365.json")


def test_inventory_setting_names_are_not_credential_shaped() -> None:
    import json
    import re

    from sspm.paths import FIXTURE_FILES, REPORT_HTML, tenant_from_report_url

    bait = re.compile(r"password|passwd|\bpwd\b|secret|token", re.I)
    for path in FIXTURE_FILES.values():
        payload = json.loads(path.read_text(encoding="utf-8"))
        for setting in payload.get("settings") or []:
            assert not bait.search(str(setting["name"])), setting["name"]
    assert tenant_from_report_url("/sspm/report/m365") == "m365"
    assert tenant_from_report_url("/sspm/report/../etc/passwd") is None
    assert tenant_from_report_url("/sspm/report/m365.json") is None
    assert REPORT_HTML["okta"].name == "okta_report.html"
