"""Stdlib Web UI for the Cloud Cost & Configuration Review."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from cost.db.store import fetch_all, init_schema
from cost.fixtures import tenant_name
from cost.language import contains_banned
from cost.paths import REPORT_MD, STATIC_HTML, ensure_output
from cost.pipeline import run_all
from cost.report_writer.service import TITLE
from cost.report_writer.service import run as write_report

Headers = dict[str, str]
DispatchResult = tuple[int, Headers, bytes]


def _embed_json(payload: Any) -> str:
    return json.dumps(payload, default=str, separators=(",", ":")).replace("<", "\\u003c")


def build_state(sandbox: bool = True) -> dict[str, Any]:
    conn = init_schema()
    costs = fetch_all(conn, "findings_costs")
    resources = fetch_all(conn, "findings_resources")
    rightsizing = fetch_all(conn, "findings_rightsizing")
    untagged = fetch_all(conn, "findings_untagged")
    drift = fetch_all(conn, "findings_drift")
    framework = fetch_all(conn, "findings_compliance")
    report_text = REPORT_MD.read_text(encoding="utf-8") if REPORT_MD.is_file() else ""
    spend = round(sum(float(r.get("amount") or 0) for r in costs), 2)
    savings = round(sum(float(r.get("monthly_savings_estimate") or 0) for r in rightsizing), 2)
    return {
        "title": TITLE,
        "tenant": tenant_name(),
        "sandbox": sandbox,
        "totals": {
            "spend": spend,
            "rightsizing_savings": savings,
            "resources": len(resources),
            "untagged": len(untagged),
            "drift": len(drift),
        },
        "costs": costs,
        "resources": resources,
        "rightsizing": rightsizing,
        "untagged": untagged,
        "drift": drift,
        "framework": framework,
        "report_markdown": report_text,
        "banned_in_report": contains_banned(report_text),
        "routes": {
            "ui": "/cost",
            "status": "/api/cost/status",
            "report": "/api/cost/report",
            "scan": "/api/cost/scan",
        },
        "cli": {
            "scan": "python -m cost scan-all --sandbox",
            "ui": "python -m cost ui --port 8765",
            "static": "python -m cost ui --static",
            "ew_tool": "python3 ew_tool.py --cost-ui --static",
        },
        "honesty": {
            "real_time": False,
            "lag": "24-48h on live cost APIs",
            "rightsizing": "heuristic; review with engineering before applying",
            "destructive": False,
        },
    }


def render_html(state: dict[str, Any] | None = None) -> str:
    payload = state if state is not None else build_state()
    snippet = f'<script type="application/json" id="embedded-state">{_embed_json(payload)}</script>\n</head>'
    return COST_HTML.replace("</head>", snippet, 1)


def write_static_html(path: Path | None = None) -> Path:
    ensure_output()
    dest = path or STATIC_HTML
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_html(), encoding="utf-8")
    return dest


def dispatch_cost(
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]] | None = None,
    body: bytes = b"",
    *,
    root_is_cost: bool = False,
) -> DispatchResult | None:
    path = path.rstrip("/") or "/"
    method = (method or "GET").upper()
    query = query or {}
    html_hdr = {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}
    json_hdr = {"Content-Type": "application/json", "Cache-Control": "no-store"}

    if method == "POST" and path in ("/api/cost/scan", "/cost/scan"):
        result = run_all(sandbox=True)
        write_report(sandbox=True)
        payload = json.dumps(
            {"ok": True, "scan": {"ok": result.get("ok")}, "state": build_state()}, default=str
        ).encode()
        return 200, json_hdr, payload

    if method != "GET":
        return None

    if path in ("/cost", "/cost/") or (root_is_cost and path == "/"):
        return 200, html_hdr, render_html().encode("utf-8")
    if path == "/api/cost/status":
        return 200, json_hdr, json.dumps(build_state(), indent=2, default=str).encode()
    if path == "/api/cost/report":
        text = REPORT_MD.read_text(encoding="utf-8") if REPORT_MD.is_file() else ""
        return 200, json_hdr, json.dumps({"markdown": text, "title": TITLE}, indent=2).encode()
    return None


def serve_cost_http(
    handler: Any,
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]],
    body: bytes = b"",
    *,
    root_is_cost: bool = False,
) -> bool:
    result = dispatch_cost(method, path, query, body, root_is_cost=root_is_cost)
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


def run_ui(*, host: str = "0.0.0.0", port: int = 8765, static: bool = False, sandbox: bool = True) -> dict[str, Any]:
    if not REPORT_MD.is_file():
        run_all(sandbox=sandbox)
    if static:
        path = write_static_html()
        print(path.resolve().as_uri())
        print(str(path.resolve()))
        return {"ok": True, "static": str(path), "sandbox": sandbox}
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse

    from cost.paths import REPO_ROOT

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if serve_cost_http(self, "GET", parsed.path, parse_qs(parsed.query), root_is_cost=True):
                return
            if parsed.path in ("/", "/cost") and serve_cost_http(self, "GET", "/cost", {}, root_is_cost=True):
                return
            super().do_GET()

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if serve_cost_http(self, "POST", parsed.path, parse_qs(parsed.query), raw):
                return
            self.send_error(404, "Not found")

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"http://127.0.0.1:{port}/cost", flush=True)
    print(f"[cost-ui] Bound to {host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return {"ok": True, "host": host, "port": port}


COST_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cloud Cost &amp; Configuration Review</title>
  <style>
    :root { --bg:#0d1117; --card:#161b22; --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --ok:#3fb950; --warn:#d29922; }
    body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
    header { padding:1.2rem 1.5rem; border-bottom:1px solid #30363d; display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; }
    h1 { margin:0; font-size:1.25rem; }
    a { color:var(--accent); }
    main { padding:1.25rem 1.5rem 3rem; max-width:1100px; margin:0 auto; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:0.75rem; margin:1rem 0; }
    .card { background:var(--card); border:1px solid #30363d; border-radius:10px; padding:0.9rem; }
    .n { font-size:1.4rem; font-weight:700; }
    .muted { color:var(--muted); font-size:0.85rem; }
    table { width:100%; border-collapse:collapse; font-size:0.85rem; }
    th, td { text-align:left; padding:0.4rem 0.5rem; border-bottom:1px solid #30363d; vertical-align:top; }
    button { background:#238636; color:white; border:0; padding:0.45rem 0.8rem; border-radius:6px; cursor:pointer; }
    pre { white-space:pre-wrap; background:#010409; padding:0.8rem; border-radius:8px; overflow:auto; max-height:420px; }
    nav a { margin-right:0.8rem; }
    .warn { color:var(--warn); }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Cloud Cost &amp; Configuration Review</h1>
      <p class="muted" id="tenant"></p>
    </div>
    <nav>
      <a href="/cost">Cost UI</a>
      <a href="/monetize">Monetize</a>
      <a href="/tape-to-cloud">Tape-to-Cloud</a>
      <a href="/monitor">Monitor</a>
    </nav>
  </header>
  <main>
    <p class="muted">Read-only review. Cost APIs lag 24–48h. Rightsizing is heuristic — review with engineering before applying. Not a security assessment.</p>
    <p><button id="scan" type="button">Run sandbox scan</button> <span class="muted" id="scan-status"></span></p>
    <div class="grid" id="kpis"></div>
    <section class="card"><h2>Top cost drivers</h2><div id="costs"></div></section>
    <section class="card"><h2>Rightsizing observations</h2><p class="muted">Review with the engineering team before applying.</p><div id="rs"></div></section>
    <section class="card"><h2>Untagged inventory</h2><div id="un"></div></section>
    <section class="card"><h2>Configuration drift</h2><div id="drift"></div></section>
    <section class="card"><h2>Framework references</h2><div id="fw"></div></section>
    <section class="card"><h2>Report</h2><pre id="report"></pre></section>
    <section class="card"><h2>CLI</h2><pre id="cli"></pre></section>
  </main>
  <script>
    const embedded = document.getElementById('embedded-state');
    let state = embedded ? JSON.parse(embedded.textContent) : null;
    function table(headers, rows) {
      if (!rows.length) return '<p class="muted">None in this review window.</p>';
      const th = headers.map(h => '<th>'+h+'</th>').join('');
      const tr = rows.map(r => '<tr>'+r.map(c => '<td>'+c+'</td>').join('')+'</tr>').join('');
      return '<table><thead><tr>'+th+'</tr></thead><tbody>'+tr+'</tbody></table>';
    }
    function paint(s) {
      document.getElementById('tenant').textContent = (s.tenant || '') + (s.sandbox ? ' · sandbox fixtures' : ' · live APIs');
      const t = s.totals || {};
      document.getElementById('kpis').innerHTML = [
        ['Spend USD', t.spend],
        ['Rightsizing est.', t.rightsizing_savings],
        ['Resources', t.resources],
        ['Untagged', t.untagged],
        ['Drift rows', t.drift]
      ].map(([k,v]) => '<div class="card"><div class="muted">'+k+'</div><div class="n">'+(v ?? '—')+'</div></div>').join('');
      document.getElementById('costs').innerHTML = table(['Provider','Service','Amount'],
        (s.costs||[]).map(r => [r.provider, r.service, Number(r.amount).toFixed(2)]));
      document.getElementById('rs').innerHTML = table(['Resource','Current','Suggested','Savings','Risk'],
        (s.rightsizing||[]).map(r => [r.resource_id, r.current_type, r.recommended_type, Number(r.monthly_savings_estimate).toFixed(2), r.risk_level]));
      document.getElementById('un').innerHTML = table(['Resource','Missing tags','Cost'],
        (s.untagged||[]).map(r => [r.resource_id, r.missing_tags, Number(r.monthly_cost).toFixed(2)]));
      document.getElementById('drift').innerHTML = table(['Resource','Field','Baseline','Current'],
        (s.drift||[]).map(r => [r.resource_id, r.field, r.baseline, r.current_value]));
      document.getElementById('fw').innerHTML = table(['Control','Name','Status'],
        (s.framework||[]).map(r => [r.control_id, r.control_name, r.status]));
      document.getElementById('report').textContent = s.report_markdown || 'Run a scan to generate report.md';
      document.getElementById('cli').textContent = JSON.stringify(s.cli, null, 2);
    }
    async function load() {
      try {
        const res = await fetch('/api/cost/status', {cache:'no-store'});
        if (res.ok) state = await res.json();
      } catch (e) { /* file:// uses embedded state */ }
      if (state) paint(state);
    }
    document.getElementById('scan').addEventListener('click', async () => {
      const el = document.getElementById('scan-status');
      el.textContent = 'scanning…';
      try {
        const res = await fetch('/api/cost/scan', {method:'POST'});
        const data = await res.json();
        state = data.state || state;
        paint(state);
        el.textContent = 'done';
      } catch (e) {
        el.textContent = 'scan needs the live server (not file://)';
      }
    });
    load();
  </script>
</body>
</html>
"""
