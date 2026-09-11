"""SSPM stdlib web explorer."""

from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from sspm.web.app import SspmHandler, dashboard_state, render_html, write_static

_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})


def _http(host: str, port: int, method: str, path: str, *, timeout: float) -> tuple[int, str]:
    """Talk to the in-process explorer. http.client has no file:// handler."""
    if host not in _LOOPBACK:
        raise AssertionError(f"refusing non-loopback test host {host!r}")
    conn = HTTPConnection(host, int(port), timeout=timeout)
    try:
        body = b"" if method == "POST" else None
        conn.request(method, path, body=body)
        resp = conn.getresponse()
        return resp.status, resp.read().decode("utf-8")
    finally:
        conn.close()


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
        status, body = _http(host, port, "GET", "/api/sspm/health", timeout=10)
        assert status == 200
        assert json.loads(body)["status"] == "ok"
        status, page = _http(host, port, "GET", "/sspm", timeout=10)
        assert status == 200
        assert "Inventory Explorer" in page
        status, api = _http(host, port, "GET", "/api/sspm", timeout=10)
        assert status == 200
        assert json.loads(api)["oauth"]
        status, scanned = _http(host, port, "POST", "/api/sspm/scan", timeout=30)
        assert status == 200
        payload = json.loads(scanned)
        assert payload["oauth"]
        status, report = _http(host, port, "GET", "/sspm/report/m365", timeout=10)
        assert status == 200
        assert "Configuration" in report
        status, _missing = _http(host, port, "GET", "/sspm/report/../etc/passwd", timeout=10)
        assert status == 404
        status, _unknown = _http(host, port, "GET", "/sspm/report/not-a-tenant", timeout=10)
        assert status == 404
    finally:
        httpd.shutdown()
