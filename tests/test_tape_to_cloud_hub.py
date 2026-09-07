"""Tests for tape-to-cloud Web UI hub."""

from __future__ import annotations

from engine.tape_to_cloud_hub import build_hub_state, dispatch_tape_to_cloud, render_hub_html


def test_build_hub_state_has_sixteen_modules():
    state = build_hub_state()
    assert state["module_count"] == 16
    assert state["layer_count"] == 6
    assert "tape-vault" in state["modules"]
    assert "integrity" in state["layers"]
    assert state["packages"]["tape_to_cloud_ingest"] is True
    assert state["packages"]["tape_to_cloud_monetize"] is True
    assert state["packages"]["forum_watcher"] is True
    assert state["web_routes"]["jobs"] == "/tape-to-cloud/jobs"
    assert state["web_routes"]["reports"] == "/tape-to-cloud/reports"
    assert state["web_routes"]["validation"] == "/tape-to-cloud/validation"
    assert "live_jobs" in state
    assert "working" in state["honesty"]


def test_dispatch_tape_to_cloud_html_and_api():
    html = dispatch_tape_to_cloud("GET", "/tape-to-cloud")
    assert html is not None
    assert html[0] == 200
    assert b"Tape-to-Cloud Hub" in html[2]

    api = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/status")
    assert api is not None
    assert b'"module_count": 16' in api[2]

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


def test_render_hub_html_includes_discovery_docs():
    html = render_hub_html()
    assert "free-tool-inventory.md" in html
    assert "/monetize" in html
    assert "/tape-to-cloud/reports" in html
    assert "rpt-audit-cma-2026-q1" in html
    assert "6 cross-cutting layers" in html
    assert "INTACT" in html
    assert "Live ingest jobs" in html
    assert "python -m tape_to_cloud ingest" in html
    assert "/tape-to-cloud/jobs" in html
