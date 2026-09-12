"""Stdlib SSPM Explorer (no Flask/FastAPI)."""

from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from sspm import MODULES, __version__
from sspm.audit.service import inventory
from sspm.compliance_map.service import map_tenant
from sspm.config_drift.service import diff_tenant
from sspm.disclaimers.service import show
from sspm.oauth_grants.service import list_grants_dicts
from sspm.paths import report_html_file, report_md_file, tenant_from_report_url
from sspm.report_writer.service import generate

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8767
ROOT = Path(__file__).resolve().parents[2]


def dashboard_state() -> dict[str, Any]:
    inv = inventory(write=False)
    reports = {}
    for tenant in ("m365", "gws", "github", "slack", "okta"):
        out = report_md_file(tenant)
        if not out.exists():
            generate(tenant=tenant, output=out)
        reports[tenant] = {
            "markdown": str(out),
            "html": str(out.with_suffix(".html")),
            "json": str(out.with_suffix(".json")),
        }
    oauth = list_grants_dicts(tenant="all")
    drift = [d.model_dump() for d in diff_tenant(tenant="m365")]
    refs = [r.model_dump() for r in map_tenant(framework="cis-m365", tenant="m365")]
    high = sum(1 for g in oauth if g["risk_level"] == "high")
    return {
        "service": "sspm-web",
        "version": __version__,
        "title": "Configuration & Inventory Explorer",
        "modules": list(MODULES),
        "inventory": inv,
        "oauth": oauth,
        "oauth_high": high,
        "drift_m365": drift,
        "control_refs_m365": refs,
        "reports": reports,
        "disclaimer": show().text,
        "honest_gap": (
            "This explorer is a read-only Configuration & Inventory view. "
            "It is not AppOmni. Live APIs run only when SSPM_LIVE=1 is set."
        ),
    }


def render_html(state: dict[str, Any] | None = None) -> str:
    state = state or dashboard_state()
    css = """
:root { --bg:#0b1220; --card:#121a2b; --line:#1f2a44; --text:#e8eefc; --muted:#93a0bf; --accent:#6ea8fe; --warn:#fbbf24; --ok:#34d399; }
* { box-sizing:border-box; }
body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
header { padding:1.25rem 2rem; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; }
header h1 { margin:0; font-size:1.15rem; }
header small { color:var(--muted); }
.layout { display:grid; grid-template-columns: 240px 1fr; min-height: calc(100vh - 64px); }
nav { border-right:1px solid var(--line); padding:1rem; }
nav button { display:block; width:100%; text-align:left; background:transparent; color:var(--text); border:0; padding:.6rem .8rem; border-radius:8px; cursor:pointer; }
nav button.active, nav button:hover { background:var(--card); }
#scan { background:var(--accent); color:#0b1220; border:0; padding:.55rem 1rem; border-radius:8px; cursor:pointer; font-weight:600; margin-right:.75rem; }
#scan:disabled { opacity:.6; cursor:wait; }
main { padding:1.5rem 2rem; }
.cards { display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap:1rem; }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1rem; }
.card .n { font-size:1.6rem; font-weight:700; color:var(--accent); }
table { width:100%; border-collapse:collapse; font-size:.9rem; }
th, td { border-bottom:1px solid var(--line); padding:.45rem .4rem; text-align:left; vertical-align:top; }
.muted { color:var(--muted); }
.panel { display:none; }
.panel.active { display:block; }
pre { white-space:pre-wrap; background:#0a0f1a; padding:1rem; border-radius:8px; overflow:auto; max-height:480px; }
.badge { display:inline-block; padding:.1rem .45rem; border-radius:999px; background:#1d283f; color:var(--warn); font-size:.75rem; }
a { color:var(--accent); }
"""
    oauth_rows = "".join(
        f"<tr><td>{g['tenant_type']}</td><td>{g['app_name']}</td><td>{g['publisher']}</td>"
        f"<td><code>{g['scopes']}</code></td><td class='badge'>{g['risk_level']}</td></tr>"
        for g in state["oauth"]
    )
    drift_rows = "".join(
        f"<tr><td><code>{d['setting_name']}</code></td><td>{d.get('old_value')}</td><td>{d.get('new_value')}</td></tr>"
        for d in state["drift_m365"]
    )
    ref_rows = "".join(
        f"<tr><td>{r['control_id']}</td><td>{r['title']}</td><td>{r['reference_status']}</td></tr>"
        for r in state["control_refs_m365"]
    )
    report_links = "".join(f"<li>{kind}: <a href='/sspm/report/{kind}'>open HTML</a></li>" for kind in state["reports"])
    module_list = "".join(f"<li><code>sspm/{m}</code></li>" for m in state["modules"])
    disclaimer = state["disclaimer"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SSPM Configuration &amp; Inventory Explorer</title>
<style>{css}</style>
</head><body>
<header>
  <div>
    <h1>SSPM Configuration &amp; Inventory Explorer</h1>
    <small>v{state["version"]} · read-only · not an attestation</small>
  </div>
  <small>Mondoo cnspec backbone · $0/month lane</small>
</header>
<div class="layout">
  <nav>
    <button class="active" data-panel="dash">Dashboard</button>
    <button data-panel="oauth">OAuth grants</button>
    <button data-panel="drift">Drift</button>
    <button data-panel="refs">Control references</button>
    <button data-panel="reports">Reports</button>
    <button data-panel="disclaimer">Disclaimer</button>
  </nav>
  <main>
    <section class="panel active" id="dash">
      <div class="cards">
        <div class="card"><div class="muted">Modules</div><div class="n">{len(state["modules"])}</div></div>
        <div class="card"><div class="muted">OSS tools</div><div class="n">{state["inventory"]["tool_count"]}</div></div>
        <div class="card"><div class="muted">OAuth grants</div><div class="n">{len(state["oauth"])}</div></div>
        <div class="card"><div class="muted">High-scope grants</div><div class="n">{state["oauth_high"]}</div></div>
        <div class="card"><div class="muted">M365 drift rows</div><div class="n">{len(state["drift_m365"])}</div></div>
      </div>
      <p style="margin-top:1.2rem">
        <button id="scan" type="button">Run fixture scan</button>
        <span class="muted" id="scan-status">Read-only fixtures unless SSPM_LIVE=1</span>
      </p>
      <p class="muted">{state["honest_gap"]}</p>
      <h3>12 modules</h3>
      <ul>{module_list}</ul>
    </section>
    <section class="panel" id="oauth">
      <div class="card"><h3>OAuth grants (scopes only)</h3>
      <table><thead><tr><th>Tenant</th><th>App</th><th>Publisher</th><th>Scopes</th><th>Risk</th></tr></thead>
      <tbody>{oauth_rows}</tbody></table></div>
    </section>
    <section class="panel" id="drift">
      <div class="card"><h3>M365 drift vs shipped baseline</h3>
      <table><thead><tr><th>Setting</th><th>Baseline</th><th>Current</th></tr></thead>
      <tbody>{drift_rows}</tbody></table></div>
    </section>
    <section class="panel" id="refs">
      <div class="card"><h3>CIS-M365 control references</h3>
      <p class="muted">Mapping aid only — not a control status.</p>
      <table><thead><tr><th>ID</th><th>Title</th><th>Reference</th></tr></thead>
      <tbody>{ref_rows}</tbody></table></div>
    </section>
    <section class="panel" id="reports">
      <div class="card">
        <h3>Generated reports</h3>
        <ul>{report_links}</ul>
        <p class="muted">On Cursor Cloud use <code>python3 ew_tool.py --sspm-ui --static</code> and open <code>reports/sspm_explorer.html</code>.</p>
      </div>
    </section>
    <section class="panel" id="disclaimer">
      <div class="card"><pre>{disclaimer}</pre></div>
    </section>
  </main>
</div>
<script>
document.querySelectorAll('nav button').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.panel).classList.add('active');
  }});
}});
const scanBtn = document.getElementById('scan');
if (scanBtn) {{
  scanBtn.addEventListener('click', async () => {{
    scanBtn.disabled = true;
    scanBtn.textContent = 'Scanning…';
    try {{
      const r = await fetch('/api/sspm/scan', {{method: 'POST'}});
      if (!r.ok) throw new Error(String(r.status));
      location.reload();
    }} catch (err) {{
      scanBtn.disabled = false;
      scanBtn.textContent = 'Run fixture scan';
      document.getElementById('scan-status').textContent = 'Scan failed: ' + err;
    }}
  }});
}}
</script>
</body></html>
"""


STATIC_EXPLORER_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SSPM Configuration &amp; Inventory Explorer</title>
</head><body>
<h1>SSPM Configuration &amp; Inventory Explorer</h1>
<p>read-only · not an attestation</p>
<p>Static snapshot. Use the live explorer for OAuth grants and fixture rows.</p>
<p><button type="button" disabled>Run fixture scan</button> (live server only)</p>
</body></html>
"""


def write_static(output_dir: str = "reports") -> dict[str, str]:
    cwd = Path.cwd().resolve()
    (cwd / "output" / "sspm").mkdir(parents=True, exist_ok=True)
    (cwd / "output" / "sspm" / "explorer_state.json").write_text(
        '{"service":"sspm-web","static":true}\n', encoding="utf-8"
    )
    state_path = str(cwd / "output" / "sspm" / "explorer_state.json")
    if output_dir == "reports":
        (cwd / "reports").mkdir(parents=True, exist_ok=True)
        (cwd / "reports" / "sspm_explorer.html").write_text(STATIC_EXPLORER_HTML, encoding="utf-8")
        return {"html": str(cwd / "reports" / "sspm_explorer.html"), "state": state_path}
    (cwd / "sspm_explorer.html").write_text(STATIC_EXPLORER_HTML, encoding="utf-8")
    return {"html": str(cwd / "sspm_explorer.html"), "state": state_path}


class SspmHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        if args and str(args[0]).startswith("GET /api/"):
            return
        super().log_message(fmt, *args)

    def _json(self, payload: object, code: int = 200) -> None:
        body = json.dumps(payload, indent=2, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._html(render_html())
            return
        if serve_sspm_http(self, "GET", path, parse_qs(parsed.query)):
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if serve_sspm_http(self, "POST", parsed.path, parse_qs(parsed.query), body):
            return
        self.send_error(404, "Not found")


def _send_json(handler: Any, payload: object, code: int = 200) -> None:
    body = json.dumps(payload, indent=2, default=str).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _send_html(handler: Any, html: str, code: int = 200) -> None:
    body = html.encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def serve_sspm_http(handler: Any, method: str, path: str, _query: dict, _body: bytes = b"") -> bool:
    """Shared routes for `sspm web` and `--monitor`."""
    if method == "POST" and path == "/api/sspm/scan":
        from sspm.cli import main as sspm_main

        sspm_main(["--persist", "demo"])
        _send_json(handler, dashboard_state())
        return True
    if method != "GET":
        return False
    if path in ("/sspm", "/sspm/"):
        _send_html(handler, render_html())
        return True
    if path == "/api/sspm":
        _send_json(handler, dashboard_state())
        return True
    if path == "/api/sspm/health":
        _send_json(handler, {"status": "ok", "service": "sspm-web", "version": __version__})
        return True
    if path.startswith("/sspm/report/"):
        tenant = tenant_from_report_url(path)
        if tenant is None:
            handler.send_error(404, "unknown tenant")
            return True
        return _serve_tenant_report(handler, tenant)
    return False


def _serve_tenant_report(handler: Any, tenant: str) -> bool:
    if tenant == "m365":
        report = report_html_file("m365")
        md = report_md_file("m365")
        kind = "m365"
    elif tenant == "gws":
        report = report_html_file("gws")
        md = report_md_file("gws")
        kind = "gws"
    elif tenant == "github":
        report = report_html_file("github")
        md = report_md_file("github")
        kind = "github"
    elif tenant == "slack":
        report = report_html_file("slack")
        md = report_md_file("slack")
        kind = "slack"
    elif tenant == "okta":
        report = report_html_file("okta")
        md = report_md_file("okta")
        kind = "okta"
    else:
        handler.send_error(404, "unknown tenant")
        return True
    if report.exists():
        _send_html(handler, report.read_text(encoding="utf-8"))
        return True
    generate(tenant=kind, output=md)
    if report.exists():
        _send_html(handler, report.read_text(encoding="utf-8"))
        return True
    handler.send_error(404, "report not generated")
    return True


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    write_static()
    server = ThreadingHTTPServer((host, port), SspmHandler)
    print(f"http://127.0.0.1:{port}/sspm")
    print(f"[sspm-ui] Bound to {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[sspm-ui] stopped")
        server.shutdown()
