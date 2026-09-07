"""Platform module tests — catalog, governance, siem, observability, warehouse."""

from pathlib import Path

from dspm.catalog.service import build_lineage_graph, register_asset
from dspm.governance.service import apply_mask, seed_policies
from dspm.observability.service import dashboard_summary, seed_alert_rules
from dspm.siem.service import ingest_event, search_events
from dspm.store.db import init_db
from dspm.warehouse.service import execute_sql, query_history


def test_governance_masking():
    seed_policies()
    masked = apply_mask("john@example.com", "PII", "DATA_USER")
    assert masked != "john@example.com"
    full = apply_mask("john@example.com", "PII", "DATA_ADMIN")
    assert full == "john@example.com"


def test_siem_ingest_and_search():
    init_db()
    ingest_event("test", "low", "unit", "unique search token xyz123")
    results = search_events("xyz123")
    assert any("xyz123" in e.get("message", "") for e in results)


def test_warehouse_sql():
    init_db()
    result = execute_sql("SELECT COUNT(*) AS cnt FROM findings")
    assert "rows" in result
    assert result["rows"][0]["cnt"] >= 1


def test_catalog_register():
    init_db()
    asset = register_asset("test_table", "table", owner="qa")
    assert "urn:dspm:asset" in asset["urn"]
    graph = build_lineage_graph()
    assert "nodes" in graph


def test_observability_dashboard():
    summary = dashboard_summary(
        [{"type": "PII"}],
        [{"score": 85}],
        [{"severity": "critical"}],
    )
    assert summary["findings_total"] == 1
    assert seed_alert_rules()
