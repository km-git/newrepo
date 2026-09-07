"""DMARC hub — stdlib Web UI routes for the EW monitor server."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DMARC_ROOT = ROOT / "dmarc"


def _dmarc_available() -> bool:
    return (DMARC_ROOT / "dmarc" / "cli.py").is_file()


def build_hub_state() -> dict[str, Any]:
    state: dict[str, Any] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "available": _dmarc_available(),
        "web_ui": "python -m dmarc web serve --port 8767",
        "cli_scan": "python -m dmarc scan --domain example.com.au",
        "make_target": "make -C dmarc dmarc-all",
    }
    if not _dmarc_available():
        return state
    try:
        from dmarc.db import count_rows, fetch_all, init_db

        init_db()
        state["counts"] = {
            "dns": count_rows("findings_dns"),
            "spf": count_rows("findings_spf"),
            "dkim": count_rows("findings_dkim"),
            "dmarc": count_rows("findings_dmarc"),
            "inbox": count_rows("findings_inbox"),
        }
        state["recent_dmarc"] = fetch_all("findings_dmarc", limit=5)
    except Exception as exc:
        state["error"] = str(exc)
    discoveries = DMARC_ROOT / "discoveries"
    if discoveries.is_dir():
        files = sorted(discoveries.glob("*.md"), reverse=True)
        if files:
            state["latest_discovery"] = files[0].name
    return state


def _html_page(state: dict[str, Any]) -> str:
    counts = state.get("counts") or {}
    cards = "".join(
        f'<div class="card"><div class="label">{k}</div><div class="value">{v}</div></div>'
        for k, v in counts.items()
    )
    rows = ""
    for r in state.get("recent_dmarc") or []:
        rows += (
            f"<tr><td>{r.get('source_org','')}</td><td>{r.get('source_ip','')}</td>"
            f"<td>{r.get('count','')}</td><td>{r.get('dkim_result','')}</td>"
            f"<td>{r.get('spf_result','')}</td></tr>"
        )
    if not rows:
        rows = "<tr><td colspan='5'>Run <code>make -C dmarc dmarc-all</code> or POST /api/dmarc/scan</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>DMARC Hub</title>
<style>
:root {{ --bg:#0d1117; --card:#161b22; --border:#30363d; --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; }}
body {{ margin:0; font-family:system-ui,sans-serif; background:var(--bg); color:var(--text); }}
header {{ padding:1rem 1.25rem; border-bottom:1px solid var(--border); }}
main {{ padding:1.25rem; max-width:1100px; margin:0 auto; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:0.75rem; }}
.card {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:0.75rem; }}
.label {{ font-size:0.7rem; color:var(--muted); text-transform:uppercase; }}
.value {{ font-size:1.4rem; font-weight:600; }}
section {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:1rem; margin:1rem 0; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:0.4rem; border-bottom:1px solid var(--border); text-align:left; }}
a {{ color:var(--accent); }} code {{ color:var(--accent); }}
</style></head>
<body>
<header>
  <h1>Email Deliverability &amp; Brand-Protection Hub</h1>
  <p style="color:var(--muted)">Read-only DMARC / SPF / DKIM observations — not a security assessment</p>
  <nav>
    <a href="/monitor">Monitor</a> · <a href="/monetize">Monetize</a>
    · <a href="/tape-to-cloud">Tape-to-Cloud</a> · <a href="/dmarc">DMARC</a>
  </nav>
</header>
<main>
  <section><h2>Counts</h2><div class="cards">{cards or '<p>No data yet</p>'}</div></section>
  <section><h2>Recent aggregate rows</h2>
    <table>
      <thead><tr><th>Org</th><th>IP</th><th>Count</th><th>DKIM</th><th>SPF</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
  <section><h2>CLI</h2><pre>{state.get('cli_scan','')}
{state.get('web_ui','')}
{state.get('make_target','')}</pre></section>
</main></body></html>"""


def serve_dmarc_http(handler: SimpleHTTPRequestHandler, method: str, path: str, query: dict) -> bool:
    if not path.startswith("/dmarc") and not path.startswith("/api/dmarc"):
        return False
    if path in ("/dmarc", "/dmarc/"):
        state = build_hub_state()
        body = _html_page(state).encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
        return True
    if path == "/api/dmarc/status" and method == "GET":
        body = json.dumps(build_hub_state(), default=str).encode()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(body)
        return True
    if path == "/api/dmarc/scan" and method == "POST":
        domain = (query.get("domain") or ["example.com.au"])[0]
        from dmarc.cli import scan_cmd

        scan_cmd(domain=domain)
        body = json.dumps(build_hub_state(), default=str).encode()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(body)
        return True
    handler.send_error(404, "DMARC route not found")
    return True
