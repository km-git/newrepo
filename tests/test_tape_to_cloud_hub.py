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
    assert state["focus"] == "tape-to-cloud-only"
    assert len(state["sample_reports"]) == 17


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


def test_render_hub_html_includes_discovery_docs_and_reports():
    html = render_hub_html()
    assert "free-tool-inventory.md" in html
    assert "/tape-to-cloud/reports/job-pack" in html
    assert "feature-completeness.md" in html


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
    api = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/reports/job-pack")
    payload = json.loads(api[2])
    assert payload["module_count"] == 16
    assert len(payload["reports"]) == 16
    layers = dispatch_tape_to_cloud("GET", "/tape-to-cloud/layers")
    assert layers is not None and layers[0] == 200
    assert b"integrity" in layers[2]
    docs = dispatch_tape_to_cloud("GET", "/tape-to-cloud/docs/feature-completeness.md")
    assert docs is not None and docs[0] == 200
    assert b"Cross-cutting layers" in docs[2]
    assert len(list_reports()) == 17
