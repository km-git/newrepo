"""Tests for tape-to-cloud Web UI hub."""

from __future__ import annotations

import json

from engine.tape_to_cloud_hub import build_hub_state, dispatch_tape_to_cloud, render_hub_html
from tape_to_cloud.catalog import LAYERS, MODULES
from tape_to_cloud.sample_reports import get_report, list_reports


def test_build_hub_state_has_sixteen_modules():
    state = build_hub_state()
    assert state["module_count"] == 16
    assert state["layer_count"] == 6
    assert "tape-vault" in state["modules"]
    assert state["packages"]["tape_to_cloud_monetize"] is True
    assert state["packages"]["forum_watcher"] is True
    assert state["packages"]["tape_to_cloud_ingest"] is True
    assert "integrity" in state["layers"]
    assert state["focus"] == "tape-to-cloud-only"
    assert len(state["sample_reports"]) == 17
    assert state["cli"]["report"] == "python -m tape_to_cloud report audit"
    assert state["cli"]["list"] == "python -m tape_to_cloud list"
    assert state["web_routes"]["jobs"] == "/tape-to-cloud/jobs"
    assert state["web_routes"]["validation"] == "/tape-to-cloud/validation"
    assert "live_jobs" in state
    assert "working" in state["honesty"]


def test_dispatch_tape_to_cloud_html_and_api():
    html = dispatch_tape_to_cloud("GET", "/tape-to-cloud")
    assert html is not None
    assert html[0] == 200
    assert b"Tape-to-Cloud Hub" in html[2]
    assert b"/monitor" not in html[2]
    assert b"Comprehensive Media Audit" in html[2]

    home = dispatch_tape_to_cloud("GET", "/")
    assert home is not None and home[0] == 200
    assert b"16 modules" in home[2]

    api = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/status")
    assert api is not None
    assert b'"module_count": 16' in api[2]
    assert b'"layer_count": 6' in api[2]

    jobs = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/jobs")
    assert jobs is not None
    assert jobs[0] == 200
    assert b'"jobs"' in jobs[2]

    listing = dispatch_tape_to_cloud("GET", "/tape-to-cloud/jobs")
    assert listing is not None
    assert listing[0] == 200
    assert b"Live ingest jobs" in listing[2]

    missing = dispatch_tape_to_cloud("GET", "/tape-to-cloud/jobs/does-not-exist")
    assert missing is not None
    assert missing[0] == 404


def test_render_hub_html_includes_discovery_docs_and_reports():
    html = render_hub_html()
    assert "free-tool-inventory.md" in html
    assert "/tape-to-cloud/reports/job-pack" in html
    assert "feature-completeness.md" in html
    assert "tape_to_cloud.layers.apply_layers" in html
    assert "python -m tape_to_cloud report audit" in html
    assert "python -m tape_to_cloud ingest" in html
    assert "/tape-to-cloud/jobs" in html
    assert "rpt-audit-cma-2026-q1" in html
    assert "INTACT" in html
    assert "Live ingest jobs (real bytes)" in html
    assert "6 cross-cutting layers" in html


def test_every_module_has_sample_report_with_six_layers():
    assert len(MODULES) == 16
    assert len(LAYERS) == 6
    for module_id in MODULES:
        page = dispatch_tape_to_cloud("GET", f"/tape-to-cloud/modules/{module_id}")
        assert page is not None and page[0] == 200, module_id
        report_page = dispatch_tape_to_cloud("GET", f"/tape-to-cloud/reports/{module_id}")
        assert report_page is not None and report_page[0] == 200, module_id
        api = dispatch_tape_to_cloud("GET", f"/api/tape-to-cloud/reports/{module_id}")
        assert api is not None and api[0] == 200, module_id
        payload = json.loads(api[2])
        assert payload["kind"] == "sample"
        assert payload["module"] == module_id
        assert set(payload["layers_called"]) == set(LAYERS)
        assert get_report(module_id)["report_id"] == payload["report_id"]


def test_job_pack_and_layers_routes():
    pack = dispatch_tape_to_cloud("GET", "/tape-to-cloud/reports/job-pack")
    assert pack is not None and pack[0] == 200
    assert b'class="kpis"' in pack[2] or b"class='kpis'" in pack[2] or b'class="kpis"' in pack[2]
    assert b"Comprehensive Media Audit" in pack[2]
    api = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/reports/job-pack")
    payload = json.loads(api[2])
    assert payload["module_count"] == 16
    assert len(payload["reports"]) == 16
    layers = dispatch_tape_to_cloud("GET", "/tape-to-cloud/layers")
    assert layers is not None and layers[0] == 200
    assert b"integrity" in layers[2]
    assert b"tape_to_cloud.layers.apply_layers" in layers[2]
    assert b"stop-and-ask" in layers[2]
    docs = dispatch_tape_to_cloud("GET", "/tape-to-cloud/docs/feature-completeness.md")
    assert docs is not None and docs[0] == 200
    assert b"Cross-cutting layers" in docs[2]
    assert len(list_reports()) == 17


def test_detailed_reports_are_vendor_complete_html():
    from tape_to_cloud.sample_reports import AUDIT_TAPE_KEYS

    for module_id in MODULES:
        report = get_report(module_id)
        assert report["layers"]["integrity"]["primary_algo"] == "SHA-256"
        assert report["layers"]["integrity"]["md5_not_primary"] is True
        assert len(report["layers"]["integrity"]["pre_hash"]) == 64
        assert set(report["layers_called"]) == set(LAYERS)
        assert report["layers"]["format-readers"]["invented_parser"] is False
        assert report["layers"]["kms-kmip"]["refuse_if_missing"] is True
        assert report["executive_summary"]
        assert report["kpis"]
        assert report["chain_of_custody"]
    audit = get_report("audit")
    kpis = {row["label"]: row["value"] for row in audit["kpis"]}
    assert kpis["unique media types"] == 16
    assert kpis["media count"] == 2144
    assert audit["result"]["collection"]["rfid_volume_accuracy"] == "±5%"
    assert any(t["generation"] == "LTO-10" for t in audit["result"]["tapes"])
    for tape in audit["result"]["tapes"]:
        assert not (set(AUDIT_TAPE_KEYS) - set(tape))
        assert 1 <= tape["degradation"] <= 10
    pool = get_report("vtl-cloud")["result"]["tape_pool"]
    assert pool["retention_lock_type"] == "COMPLIANCE"
    assert pool["worm_at_create"] is True
    assert "800-88" in get_report("destroy")["result"]["certificate"]["nist"]
    audit_html = dispatch_tape_to_cloud("GET", "/tape-to-cloud/reports/audit")
    assert audit_html is not None and audit_html[0] == 200
    body = audit_html[2]
    assert b'class="kpis"' in body
    assert b"LTO-10" in body
    assert b"SHA-256" in body
    assert b"RFID" in body or b"rfid" in body
    assert b"Chain of custody" in body
    assert b"Recommendations" in body
    vtl = dispatch_tape_to_cloud("GET", "/tape-to-cloud/reports/vtl-cloud")[2]
    assert b"COMPLIANCE" in vtl
    destroy = dispatch_tape_to_cloud("GET", "/tape-to-cloud/reports/destroy")[2]
    assert b"800-88" in destroy
    assert b"ITAD-CERT" in destroy


def test_discovery_docs_refuse_path_escape():
    from tape_to_cloud.catalog import resolved_discovery_doc

    assert resolved_discovery_doc("feature-completeness.md") is not None
    assert resolved_discovery_doc("../engine/tape_to_cloud_hub.py") is None
    assert resolved_discovery_doc("..%2Fetc%2Fpasswd") is None
    assert dispatch_tape_to_cloud("GET", "/tape-to-cloud/docs/../../ew_tool.py") is None
    assert dispatch_tape_to_cloud("GET", "/tape-to-cloud/docs/not-a-doc.md") is None
