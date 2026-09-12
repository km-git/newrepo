"""Web UI dispatch tests for the cost review."""

from __future__ import annotations

from cost.pipeline import run_all
from cost.webui.server import dispatch_cost, render_html, write_static_html


def test_dispatch_html_and_api(tmp_path, monkeypatch):
    monkeypatch.setenv("COST_SANDBOX", "1")
    monkeypatch.setenv("COST_DB", str(tmp_path / "cost.sqlite3"))
    run_all(sandbox=True)
    html = dispatch_cost("GET", "/cost")
    assert html is not None
    assert html[0] == 200
    assert b"Cloud Cost" in html[2]

    api = dispatch_cost("GET", "/api/cost/status")
    assert api is not None
    assert api[0] == 200
    assert b'"spend"' in api[2] or b"spend" in api[2]

    report = dispatch_cost("GET", "/api/cost/report")
    assert report is not None
    assert report[0] == 200

    scan = dispatch_cost("POST", "/api/cost/scan")
    assert scan is not None
    assert scan[0] == 200

    assert dispatch_cost("GET", "/api/dashboard") is None


def test_render_html_has_disclaimer_tone(tmp_path, monkeypatch):
    monkeypatch.setenv("COST_DB", str(tmp_path / "cost.sqlite3"))
    run_all(sandbox=True)
    html = render_html()
    assert "Cloud Cost" in html
    assert "not a security assessment" in html.lower()
    assert "/api/cost/status" in html or "embedded-state" in html


def test_static_html_write(tmp_path, monkeypatch):
    monkeypatch.setenv("COST_DB", str(tmp_path / "cost.sqlite3"))
    run_all(sandbox=True)
    dest = tmp_path / "cost_explorer.html"
    path = write_static_html(dest)
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "Cloud Cost" in text
    assert "embedded-state" in text
