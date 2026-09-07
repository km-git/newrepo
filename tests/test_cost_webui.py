"""Web UI tests."""

import json
from http.server import ThreadingHTTPServer
from threading import Thread

from cost.webui.service import CostHandler, build_state, run_static


def test_build_state():
    state = build_state()
    assert state["title"] == "Cloud Cost & Configuration Review"
    assert "counts" in state


def test_static_export(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = run_static(output=tmp_path / "cost.html")
    assert path.exists()
    assert "Cloud Cost" in path.read_text(encoding="utf-8")


def test_http_handler(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), CostHandler)
    port = httpd.server_address[1]
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/cost/status", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["title"] == "Cloud Cost & Configuration Review"
    finally:
        httpd.shutdown()
