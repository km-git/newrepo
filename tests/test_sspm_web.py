"""SSPM stdlib web explorer."""

from __future__ import annotations

from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import httpx

from sspm.web.app import SspmHandler, dashboard_state, render_html, write_static


def test_dashboard_state_and_html(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SSPM_DB", str(tmp_path / "sspm.sqlite"))
    state = dashboard_state()
    assert state["service"] == "sspm-web"
    assert len(state["modules"]) == 12
    html = render_html(state)
    assert "Configuration &amp; Inventory Explorer" in html
    assert "OAuth grants" in html
    paths = write_static(str(tmp_path))
    assert Path(paths["html"]).is_file()
    assert "not an attestation" in Path(paths["html"]).read_text(encoding="utf-8")


def test_http_health_and_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SSPM_DB", str(tmp_path / "sspm.sqlite"))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), SspmHandler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    try:
        with httpx.Client(timeout=10) as client:
            health = client.get(f"http://{host}:{port}/api/sspm/health")
            assert health.status_code == 200
            assert health.json()["status"] == "ok"
            page = client.get(f"http://{host}:{port}/sspm")
            assert page.status_code == 200
            assert "Inventory Explorer" in page.text
            api = client.get(f"http://{host}:{port}/api/sspm")
            assert api.status_code == 200
            assert api.json()["oauth"]
    finally:
        httpd.shutdown()
