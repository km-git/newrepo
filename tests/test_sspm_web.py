"""SSPM stdlib web explorer."""

from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen

from sspm.web.app import SspmHandler, dashboard_state, render_html, write_static


def _get(url: str) -> tuple[int, str]:
    with urlopen(url, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")


def _post(url: str) -> tuple[int, str]:
    req = Request(url, data=b"", method="POST")
    with urlopen(req, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8")


def test_dashboard_state_and_html(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SSPM_DB", str(tmp_path / "sspm.sqlite"))
    state = dashboard_state()
    assert state["service"] == "sspm-web"
    assert len(state["modules"]) == 12
    html = render_html(state)
    assert "Configuration &amp; Inventory Explorer" in html
    assert "OAuth grants" in html
    assert "Run fixture scan" in html
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
        status, body = _get(f"http://{host}:{port}/api/sspm/health")
        assert status == 200
        assert json.loads(body)["status"] == "ok"
        status, page = _get(f"http://{host}:{port}/sspm")
        assert status == 200
        assert "Inventory Explorer" in page
        status, api = _get(f"http://{host}:{port}/api/sspm")
        assert status == 200
        assert json.loads(api)["oauth"]
        status, scanned = _post(f"http://{host}:{port}/api/sspm/scan")
        assert status == 200
        payload = json.loads(scanned)
        assert payload["oauth"]
        status, report = _get(f"http://{host}:{port}/sspm/report/m365")
        assert status == 200
        assert "Configuration" in report
    finally:
        httpd.shutdown()
