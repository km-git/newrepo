"""Tests for Monetize Explorer HTML, JSON API, and local stdlib server."""

from __future__ import annotations

import json
import sys
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from engine.monetize import FEATURE_DESCRIPTIONS, features_for_tier, known_features
from engine.monetize_ui import (
    DEMO_FEATURES,
    LICENSE_UPGRADE_HINT,
    MONETIZE_HTML,
    build_explorer_state,
    dispatch_monetize,
    publish_monetize,
    set_demo_tier,
    try_require,
    write_monetize_html,
)
from scripts.serve_monetize import MonetizeHandler


def _json(result):
    status, headers, body = result
    assert headers["Content-Type"].startswith("application/json")
    return status, json.loads(body.decode())


class TestHtmlGeneration:
    def test_html_is_self_contained_product_explorer(self):
        html = MONETIZE_HTML
        assert "Monetize Explorer" in html
        assert "Access matrix" in html
        assert "Royalty report" in html
        assert "Try a gated action" in html
        assert "--monetize-status" in html
        assert "--monetize-report" in html
        assert "EW_LICENSE_TIER" in html
        assert "/api/monetize/status" in html
        assert "/api/monetize/require" in html
        assert "cdn." not in html.lower()
        assert "unpkg" not in html.lower()
        assert "AccessController.require()" in html

    def test_write_monetize_html(self, tmp_path):
        path = write_monetize_html(str(tmp_path))
        assert path.exists()
        text = path.read_text()
        assert "Monetize Explorer" in text
        assert "Interactive tier switcher" in text

    def test_publish_monetize(self, tmp_path):
        paths = publish_monetize(str(tmp_path))
        assert (tmp_path / "monetize.html").exists()
        assert "monetize_html" in paths


class TestExplorerState:
    def test_free_matrix_matches_engine(self, monkeypatch):
        monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
        state = build_explorer_state("free")
        assert state["license"]["tier"] == "free"
        assert "tagged_at" in state["license"]
        assert "batch" in state["license"]["denied"]
        assert "single_symbol" in state["license"]["allowed"]
        assert state["license"]["descriptions"]["batch"] == FEATURE_DESCRIPTIONS["batch"]
        assert set(state["license"]["allowed"]) == set(features_for_tier("free"))
        assert {row["key"] for row in state["features"]} == set(known_features())

    def test_pro_and_enterprise_json(self):
        pro = build_explorer_state("pro")
        ent = build_explorer_state("enterprise")
        assert pro["license"]["tier"] == "pro"
        assert "batch" in pro["license"]["allowed"]
        assert "live_execution" in pro["license"]["denied"]
        assert ent["license"]["tier"] == "enterprise"
        assert ent["license"]["denied"] == []
        assert "v6_scanner" in ent["license"]["allowed"]

    def test_empty_royalty(self, monkeypatch, tmp_path):
        monkeypatch.setenv("EW_ROYALTY_REPORT_PATH", str(tmp_path / "missing.json"))
        state = build_explorer_state("free")
        assert state["royalty_empty"] is True
        assert state["royalty_report"] == {}

    def test_royalty_present(self, monkeypatch, tmp_path):
        report = tmp_path / "royalty_report.json"
        report.write_text(json.dumps({
            "tier": "pro",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "usage": {"setups_generated": 2, "signals_fired": 1, "tickers_scanned": 3},
            "detail": {"setups": ["BTC/USDT"], "signals": [], "tickers": ["BTC/USDT"]},
        }))
        monkeypatch.setenv("EW_ROYALTY_REPORT_PATH", str(report))
        state = build_explorer_state("pro")
        assert state["royalty_empty"] is False
        assert state["royalty_report"]["usage"]["setups_generated"] == 2


class TestRequire:
    def test_allowed_on_free(self):
        result = try_require("single_symbol", "free")
        assert result["ok"] is True
        assert result["exit_code"] == 0

    def test_denied_batch_on_free(self):
        result = try_require("batch", "free")
        assert result["ok"] is False
        assert result["exit_code"] == 2
        assert "batch" in result["error"]
        assert "pro" in result["error"]
        assert result["hint"] == LICENSE_UPGRADE_HINT

    def test_denied_live_on_pro(self):
        result = try_require("live_execution", "pro")
        assert result["ok"] is False
        assert result["exit_code"] == 2
        assert "enterprise" in result["error"]

    def test_enterprise_allows_v6(self):
        result = try_require("v6_scanner", "enterprise")
        assert result["ok"] is True

    def test_demo_features_are_known(self):
        known = known_features()
        assert set(DEMO_FEATURES) <= set(known)


class TestDispatch:
    def test_html_route(self):
        status, headers, body = dispatch_monetize("GET", "/monetize")
        assert status == 200
        assert "text/html" in headers["Content-Type"]
        text = body.decode()
        assert "Monetize Explorer" in text
        assert "--monetize-status" in text

    def test_root_html_when_explorer_is_home(self):
        status, headers, body = dispatch_monetize("GET", "/", root_is_monetize=True)
        assert status == 200
        assert "Monetize Explorer" in body.decode()

    def test_status_free_pro_enterprise(self, monkeypatch):
        monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
        for tier in ("free", "pro", "enterprise"):
            status, data = _json(dispatch_monetize("GET", "/api/monetize/status", {"tier": [tier]}))
            assert status == 200
            assert data["license"]["tier"] == tier
            assert isinstance(data["license"]["allowed"], list)
            assert isinstance(data["license"]["denied"], list)
            assert "tagged_at" in data["license"]

    def test_require_denied_json(self):
        status, data = _json(
            dispatch_monetize("GET", "/api/monetize/require", {"feature": ["batch"], "tier": ["free"]})
        )
        assert status == 200
        assert data["ok"] is False
        assert data["exit_code"] == 2
        assert "Upgrade via EW_LICENSE_TIER" in data["hint"]

    def test_require_missing_feature(self):
        status, data = _json(dispatch_monetize("GET", "/api/monetize/require"))
        assert status == 400
        assert data["error"] == "missing feature"

    def test_post_tier_mutates_demo_env(self, monkeypatch):
        monkeypatch.setenv("EW_LICENSE_TIER", "free")
        status, data = _json(
            dispatch_monetize(
                "POST",
                "/api/monetize/tier",
                body=b'{"tier":"enterprise"}',
                content_type="application/json",
            )
        )
        assert status == 200
        assert data["license"]["tier"] == "enterprise"
        assert set_demo_tier.__module__
        from os import environ
        assert environ["EW_LICENSE_TIER"] == "enterprise"

    def test_unknown_path_is_none(self):
        assert dispatch_monetize("GET", "/api/dashboard") is None

    def test_royalty_endpoint_empty(self, monkeypatch, tmp_path):
        monkeypatch.setenv("EW_ROYALTY_REPORT_PATH", str(tmp_path / "none.json"))
        status, data = _json(dispatch_monetize("GET", "/api/monetize/royalty"))
        assert status == 200
        assert data["royalty_empty"] is True


class TestHttpServer:
    @pytest.fixture
    def server(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), MonetizeHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield httpd
        finally:
            httpd.shutdown()
            thread.join(timeout=2)

    def _get(self, server, path):
        host, port = server.server_address[:2]
        conn = HTTPConnection(host, port, timeout=5)
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            return resp.status, resp.getheader("Content-Type"), resp.read()
        finally:
            conn.close()

    def _post(self, server, path, payload):
        host, port = server.server_address[:2]
        body = json.dumps(payload).encode()
        conn = HTTPConnection(host, port, timeout=5)
        try:
            conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            return resp.status, json.loads(resp.read().decode())
        finally:
            conn.close()

    def test_page_and_status_tiers(self, server, monkeypatch):
        monkeypatch.delenv("EW_LICENSE_TIER", raising=False)
        status, ctype, body = self._get(server, "/monetize")
        assert status == 200
        assert "html" in (ctype or "")
        text = body.decode()
        assert "Monetize Explorer" in text
        assert "Access matrix" in text

        for tier in ("free", "pro", "enterprise"):
            status, ctype, body = self._get(server, f"/api/monetize/status?tier={tier}")
            assert status == 200
            data = json.loads(body.decode())
            assert data["license"]["tier"] == tier

    def test_require_denied_over_http(self, server):
        status, ctype, body = self._get(server, "/api/monetize/require?feature=live_execution&tier=free")
        assert status == 200
        data = json.loads(body.decode())
        assert data["ok"] is False
        assert data["exit_code"] == 2
        assert "live_execution" in data["error"]

    def test_post_tier_over_http(self, server, monkeypatch):
        monkeypatch.setenv("EW_LICENSE_TIER", "free")
        status, data = self._post(server, "/api/monetize/tier", {"tier": "pro"})
        assert status == 200
        assert data["license"]["tier"] == "pro"
        assert "batch" in data["license"]["allowed"]


def test_monetize_ui_flag_in_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ew_tool.py", "--help"])
    from ew_tool import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--monetize-ui" in out
    assert "Monetize Explorer" in out


def test_monetize_ui_dispatches_to_server(monkeypatch):
    import scripts.serve_monetize as serve_monetize
    from ew_tool import main

    called = {}

    def fake_run(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(serve_monetize, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["ew_tool.py", "--monetize-ui", "--monitor-port", "8777"])
    main()
    assert called["port"] == 8777
    assert called["host"] == "127.0.0.1"
