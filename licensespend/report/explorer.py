"""LicenseSpend Explorer — stdlib HTTP + static HTML. Not a 9th first-class module."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from licensespend.constants import (
    HONEST_GAPS,
    IDLE_THRESHOLDS,
    ROOT,
    SAMPLE_AS_OF,
    SAMPLE_CLIENTS,
    include_email,
)
from licensespend.privacy import contains_raw_email
from licensespend.report.service import build, build_payload, render_pack_html

TEMPLATES = Path(__file__).resolve().parent / "templates"
STATIC_EXPLORER = ROOT / "reports" / "licensespend_explorer.html"
DEFAULT_BIND_HOST = "0.0.0.0"
DEFAULT_BIND_PORT = 8765


def _embed_json(payload: dict) -> str:
    return json.dumps(payload, default=str).replace("<", "\\u003c")


def _dump_client(payload, meta: dict[str, str]) -> dict[str, Any]:
    dumped = payload.model_dump(mode="json")
    dumped["label"] = meta["label"]
    dumped["blurb"] = meta["blurb"]
    if not include_email():
        for row in dumped.get("unused") or []:
            row["email"] = None
    return dumped


def _index_row(payload, meta: dict[str, str]) -> dict[str, Any]:
    return {
        "id": meta["id"],
        "label": meta["label"],
        "blurb": meta["blurb"],
        "reclaim_monthly_aud": payload.reclaim_monthly_aud,
        "reclaim_annual_aud": payload.reclaim_annual_aud,
        "unused_count": payload.unused_count,
        "seats_total": payload.seats_total,
        "watermark": payload.watermark,
    }


def _portfolio(index: list[dict[str, Any]]) -> dict[str, Any]:
    monthly = round(sum(float(row["reclaim_monthly_aud"]) for row in index), 2)
    return {
        "clients": len(index),
        "seats_total": sum(int(row["seats_total"]) for row in index),
        "unused_seats": sum(int(row["unused_count"]) for row in index),
        "reclaim_monthly_aud": monthly,
        "reclaim_annual_aud": round(monthly * 12, 2),
    }


def build_explorer_state(
    *,
    as_of: date | None = None,
    idle_days: int = 90,
) -> dict[str, Any]:
    as_of = as_of or SAMPLE_AS_OF
    views: dict[str, Any] = {}
    for thresh in IDLE_THRESHOLDS:
        index: list[dict[str, Any]] = []
        by_id: dict[str, Any] = {}
        for meta in SAMPLE_CLIENTS:
            payload = build_payload(client=meta["id"], as_of=as_of, idle_days=thresh)
            dumped = _dump_client(payload, meta)
            index.append(_index_row(payload, meta))
            by_id[meta["id"]] = dumped
        views[str(thresh)] = {
            "idle_days_threshold": thresh,
            "portfolio": _portfolio(index),
            "client_index": index,
            "clients": by_id,
        }
    default = views[str(idle_days)] if str(idle_days) in views else views["90"]
    return {
        "product": "licensespend",
        "as_of": as_of.isoformat(),
        "idle_days_threshold": idle_days,
        "idle_thresholds": list(IDLE_THRESHOLDS),
        "currency": "AUD",
        "disclaimer": "Draft reclaim pack for human review. Not regulated advice. Do not auto-revoke.",
        "honest_gaps": list(HONEST_GAPS),
        "portfolio": default["portfolio"],
        "client_index": default["client_index"],
        "clients": default["clients"],
        "views": views,
        "routes": {
            "ui": "/licensespend",
            "api": "/api/licensespend/status",
            "pack": "/licensespend/pack/{client}",
            "static": "reports/licensespend_explorer.html",
            "static_pack": "licensespend/{client}-license-spend.html",
        },
    }


def render_explorer_html(state: dict[str, Any] | None = None) -> str:
    state = state or build_explorer_state()
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )
    return env.get_template("explorer.html.j2").render(
        state_json=_embed_json(state),
        as_of=state["as_of"],
        disclaimer=state["disclaimer"],
        portfolio=state["portfolio"],
        client_index=state["client_index"],
        default_client=state["client_index"][0]["id"] if state["client_index"] else "acme",
    )


def write_static(
    out_dir: Path | None = None,
    *,
    as_of: date | None = None,
    idle_days: int = 90,
) -> dict[str, Any]:
    reports = Path(out_dir) if out_dir is not None else ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    pack_dir = reports / "licensespend"
    state = build_explorer_state(as_of=as_of, idle_days=idle_days)
    html = render_explorer_html(state)
    explorer_path = reports / "licensespend_explorer.html"
    explorer_path.write_text(html, encoding="utf-8")
    packs = []
    for meta in SAMPLE_CLIENTS:
        files = build(
            client=meta["id"],
            out_dir=pack_dir,
            as_of=as_of or SAMPLE_AS_OF,
            idle_days=idle_days,
        )
        packs.append(files.model_dump(mode="json"))
    for path in [explorer_path, *pack_dir.glob("*.html"), *pack_dir.glob("*.md"), *pack_dir.glob("*.json")]:
        if contains_raw_email(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"raw email leaked into {path}")
    return {
        "explorer": str(explorer_path),
        "pack_dir": str(pack_dir),
        "portfolio": state["portfolio"],
        "packs": packs,
        "as_of": state["as_of"],
    }


def dispatch_licensespend(
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]] | None = None,
) -> tuple[int, dict[str, str], bytes] | None:
    path = path.rstrip("/") or "/"
    method = (method or "GET").upper()
    if method != "GET":
        return None
    if path in ("/licensespend", "/licensespend/"):
        body = render_explorer_html().encode("utf-8")
        return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, body
    if path.startswith("/licensespend/pack/"):
        client_id = path.rsplit("/", 1)[-1].strip()
        allowed = {meta["id"] for meta in SAMPLE_CLIENTS}
        if client_id not in allowed:
            err = json.dumps({"error": "unknown client", "id": client_id}).encode("utf-8")
            return 404, {"Content-Type": "application/json"}, err
        query = query or {}
        try:
            idle = int((query.get("idle") or ["90"])[0])
        except (TypeError, ValueError):
            idle = 90
        if idle not in IDLE_THRESHOLDS:
            idle = 90
        body = render_pack_html(client=client_id, idle_days=idle).encode("utf-8")
        return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, body
    if path == "/api/licensespend/status":
        body = json.dumps(build_explorer_state(), indent=2, default=str).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body
    if path == "/api/licensespend/client":
        query = query or {}
        client_id = (query.get("id") or ["acme"])[0]
        state = build_explorer_state()
        payload = state["clients"].get(client_id)
        if payload is None:
            err = json.dumps({"error": "unknown client", "id": client_id}).encode("utf-8")
            return 404, {"Content-Type": "application/json"}, err
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body
    return None


def serve_licensespend_http(
    handler: Any,
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]],
) -> bool:
    result = dispatch_licensespend(method, path, query)
    if result is None:
        return False
    status, headers, payload = result
    handler.send_response(status)
    for key, value in headers.items():
        handler.send_header(key, value)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)
    return True


def print_launch(host: str, port: int) -> None:
    print("[licensespend-ui] LicenseSpend Explorer:")
    print()
    print(f"http://127.0.0.1:{port}/licensespend")
    print()
    print(f"[licensespend-ui] Status API: http://127.0.0.1:{port}/api/licensespend/status")
    print(f"[licensespend-ui] Bound to {host}:{port}")
    print("[licensespend-ui] On Cursor Cloud, 127.0.0.1 is the VM — use --static and open")
    print("[licensespend-ui]   reports/licensespend_explorer.html")


def print_static_launch(paths: Mapping[str, Any]) -> None:
    explorer = paths.get("explorer") or str(STATIC_EXPLORER)
    print("[licensespend-ui] Self-contained LicenseSpend Explorer (open this file):")
    print()
    print(Path(explorer).resolve().as_uri())
    print()
    print("[licensespend-ui] Sample detailed reports:")
    print(f"  {paths.get('pack_dir', 'reports/licensespend')}/")


def serve(host: str = DEFAULT_BIND_HOST, port: int = DEFAULT_BIND_PORT) -> None:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, fmt: str, *args: Any) -> None:
            if args and str(args[0]).startswith("GET /api/"):
                return
            super().log_message(fmt, *args)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/licensespend", "/licensespend/") and serve_licensespend_http(
                self, "GET", "/licensespend", parse_qs(parsed.query)
            ):
                return
            if serve_licensespend_http(self, "GET", parsed.path, parse_qs(parsed.query)):
                return
            super().do_GET()

    httpd = ThreadingHTTPServer((host, port), Handler)
    print_launch(host, port)
    httpd.serve_forever()
