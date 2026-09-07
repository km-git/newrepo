"""Tests for tape-to-cloud Web UI hub."""

from __future__ import annotations

from engine.tape_to_cloud_hub import build_hub_state, dispatch_tape_to_cloud, render_hub_html


def test_build_hub_state_has_sixteen_modules():
    state = build_hub_state()
    assert state["module_count"] == 16
    assert "tape-vault" in state["modules"]
    assert state["packages"]["tape_to_cloud_monetize"] is True
    assert state["packages"]["forum_watcher"] is True


def test_dispatch_tape_to_cloud_html_and_api():
    html = dispatch_tape_to_cloud("GET", "/tape-to-cloud")
    assert html is not None
    assert html[0] == 200
    assert b"Tape-to-Cloud Hub" in html[2]

    api = dispatch_tape_to_cloud("GET", "/api/tape-to-cloud/status")
    assert api is not None
    assert b'"module_count": 16' in api[2]


def test_render_hub_html_includes_discovery_docs():
    html = render_hub_html()
    assert "free-tool-inventory.md" in html
    assert "/monetize" in html
