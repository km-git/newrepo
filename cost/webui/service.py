"""Cost Review Web UI — stdlib HTTP server on port 8766."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from cost.audit.service import inventory
from cost.db.store import FindingsStore
from cost.report_writer.service import generate

STATIC_PATH = Path("reports/cost_explorer.html")
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8766


def build_state(*, provider: str = "aws") -> dict[str, Any]:
    store = FindingsStore()
    return {
        "title": "Cloud Cost & Configuration Review",
        "provider": provider,
        "inventory": inventory(init_db=False, write_json=False),
        "counts": {
            "resources": store.count("findings_resources"),
            "costs": store.count("findings_costs"),
            "rightsizing": store.count("findings_rightsizing"),
            "untagged": store.count("findings_untagged"),
            "drift": store.count("findings_drift"),
            "framework_references": store.count("findings_compliance"),
        },
        "report_paths": {
            "markdown": "output/cost/report.md",
            "json": "output/cost/report.json",
        },
        "cli": {
            "serve": "cost webui --host 0.0.0.0 --port 8766",
            "static": "cost webui --static",
        },
    }


def _html_page(state: dict[str, Any]) -> str:
    data = json.dumps(state, indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Cloud Cost & Configuration Review</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0b1220; color: #e8eef7; }}
    h1 {{ color: #7dd3fc; }}
    .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
    pre {{ overflow: auto; background: #0f172a; padding: 1rem; border-radius: 6px; }}
    a {{ color: #93c5fd; }}
  </style>
</head>
<body>
  <h1>Cloud Cost &amp; Configuration Review</h1>
  <p>Read-only cost observations and configuration references — not a security assessment.</p>
  <div class="card">
    <h2>Dashboard</h2>
    <pre id="state">{data}</pre>
  </div>
  <div class="card">
    <h2>Actions</h2>
    <ul>
      <li><a href="/api/cost/status">Status JSON</a></li>
      <li><a href="/api/cost/report">Generate report</a></li>
    </ul>
  </div>
</body>
</html>"""


class CostHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        provider = (qs.get("provider") or ["aws"])[0]
        if parsed.path in {"/", "/cost", "/cost/"}:
            state = build_state(provider=provider)
            html = _html_page(state).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/cost/status":
            self._send(200, json.dumps(build_state(provider=provider), indent=2).encode("utf-8"))
            return
        if parsed.path == "/api/cost/report":
            payload = generate(provider=provider)
            self._send(200, json.dumps(payload, indent=2).encode("utf-8"))
            return
        self._send(404, b'{"error":"not found"}')


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    httpd = ThreadingHTTPServer((host, port), CostHandler)
    print(f"[cost-webui] Open http://127.0.0.1:{port}/cost")
    print(f"[cost-webui] Status API: http://127.0.0.1:{port}/api/cost/status")
    print(f"[cost-webui] Bound to {host}:{port}")
    print("[cost-webui] Static export: cost webui --static")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[cost-webui] stopped")


def run_static(output: Path | None = None) -> Path:
    target = output or STATIC_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    state = build_state()
    target.write_text(_html_page(state), encoding="utf-8")
    print(f"[cost-webui] wrote {target}")
    print(f"[cost-webui] Open file://{target.resolve()}")
    return target


def main() -> None:
    host = os.environ.get("COST_WEBUI_HOST", DEFAULT_HOST)
    port = int(os.environ.get("COST_WEBUI_PORT", str(DEFAULT_PORT)))
    if os.environ.get("COST_WEBUI_STATIC") == "1":
        run_static()
    else:
        run_server(host=host, port=port)


if __name__ == "__main__":
    main()
