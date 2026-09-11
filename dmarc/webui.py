"""Stdlib HTTP dashboard for the deliverability toolkit (no Flask/FastAPI)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from dmarc.aggregate_report.service import summarize
from dmarc.audit.service import run_inventory
from dmarc.dkim_check.service import check_domain as check_dkim
from dmarc.dns_check.service import check_domain as check_dns
from dmarc.forbidden import sanitize_report_text
from dmarc.paths import DISCLAIMER_PATH, STATIC_EXPLORER, output_dir
from dmarc.report_writer.service import generate as generate_report
from dmarc.spf_parser.service import parse_domain
from dmarc.store import fetch_all, utcnow

DEFAULT_BIND_HOST = "0.0.0.0"  # noqa: S104 — stdlib dashboard bind (AGENTS.md)
DEFAULT_BIND_PORT = 8765
Headers = dict[str, str]
DispatchResult = tuple[int, Headers, bytes]


def _q(query: Mapping[str, Sequence[str]], key: str) -> str:
    vals = query.get(key) or []
    return str(vals[0]) if vals else ""


def _json_bytes(payload: Any, status: int = 200) -> DispatchResult:
    blob = json.dumps(payload, indent=2, default=str).encode("utf-8")
    return status, {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}, blob


def _parse_body(body: bytes | None, content_type: str) -> dict:
    if not body:
        return {}
    text = body.decode("utf-8", "replace")
    if "application/json" in (content_type or "") or text[:1] in "{[":
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {"_parse_error": True}
    parsed = parse_qs(text)
    return {k: v[0] if v else "" for k, v in parsed.items()}


def dashboard_state(domain: str | None = None, root: Path | None = None) -> dict[str, Any]:
    domain = domain or "example.com.au"
    return {
        "title": "Email Deliverability & Brand-Protection Review",
        "generated_at": utcnow(),
        "domain": domain,
        "inventory": run_inventory(root),
        "dns": fetch_all("findings_dns", domain=domain, root=root),
        "spf": fetch_all("findings_spf", domain=domain, root=root),
        "dkim": fetch_all("findings_dkim", domain=domain, root=root),
        "aggregate": summarize(domain=domain, since="30d", root=root),
        "forensic": fetch_all("findings_forensic", domain=domain, root=root),
        "inbox": fetch_all("findings_inbox", root=root),
        "disclaimer": DISCLAIMER_PATH.read_text(encoding="utf-8") if DISCLAIMER_PATH.exists() else "",
    }


def run_check(domain: str, root: Path | None = None) -> dict[str, Any]:
    dns = check_dns(domain, root=root)
    spf = parse_domain(domain, root=root)
    dkim = check_dkim(domain, root=root)
    return {"domain": domain, "dns": dns, "spf": spf, "dkim": dkim, "checked_at": utcnow()}


def render_explorer_html(state: dict[str, Any] | None = None, embedded: bool = False) -> str:
    state = state or dashboard_state()
    blob = json.dumps(state, default=str)
    disclaimer = sanitize_report_text(state.get("disclaimer") or "")
    boot = "const EMBEDDED = " + blob + ";" if embedded else "const EMBEDDED = null;"
    return EXPLORER_HTML.replace("/*BOOT*/", boot).replace("/*DISCLAIMER*/", json.dumps(disclaimer))


def dispatch_dmarc(
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]] | None = None,
    body: bytes | None = None,
    *,
    content_type: str = "",
    root_is_dmarc: bool = False,
    output_root: Path | None = None,
) -> DispatchResult | None:
    query = query or {}
    method = (method or "GET").upper()
    path = path.rstrip("/") or "/"
    html_paths = {"/dmarc"}
    if root_is_dmarc:
        html_paths.add("/")
    if method == "GET" and path in html_paths:
        html = render_explorer_html(dashboard_state(_q(query, "domain") or None, output_root)).encode("utf-8")
        return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, html
    if path == "/api/dmarc/status" and method == "GET":
        return _json_bytes(dashboard_state(_q(query, "domain") or None, output_root))
    if path == "/api/dmarc/check" and method in ("GET", "POST"):
        parsed = _parse_body(body, content_type) if method == "POST" else {}
        domain = parsed.get("domain") or _q(query, "domain")
        if not domain:
            return _json_bytes({"error": "missing domain"}, 400)
        return _json_bytes(run_check(str(domain), output_root))
    if path == "/api/dmarc/report" and method in ("GET", "POST"):
        parsed = _parse_body(body, content_type) if method == "POST" else {}
        domain = parsed.get("domain") or _q(query, "domain") or "example.com.au"
        live = str(parsed.get("live") or _q(query, "live") or "0") in {"1", "true", "yes"}
        result = generate_report(str(domain), root=output_root, run_live=live)
        return _json_bytes(result)
    return None


def write_http_dispatch(handler: Any, result: DispatchResult) -> None:
    status, headers, payload = result
    handler.send_response(status)
    for key, value in headers.items():
        handler.send_header(key, value)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def serve_dmarc_http(
    handler: Any,
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]],
    body: bytes = b"",
    *,
    content_type: str = "",
    root_is_dmarc: bool = False,
) -> bool:
    result = dispatch_dmarc(
        method,
        path,
        query,
        body,
        content_type=content_type,
        root_is_dmarc=root_is_dmarc,
        output_root=Path(getattr(handler, "output_dir", "output/dmarc")),
    )
    if result is None:
        return False
    write_http_dispatch(handler, result)
    return True


def publish_static(output_root: Path | None = None) -> dict[str, str]:
    state = dashboard_state(root=output_root)
    html = render_explorer_html(state, embedded=True)
    dest = STATIC_EXPLORER
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    live = output_dir(output_root) / "dmarc_explorer.html"
    live.write_text(html, encoding="utf-8")
    return {"static": str(dest), "output": str(live)}


def print_explorer_launch(host: str, port: int) -> None:
    print(f"http://127.0.0.1:{port}/dmarc")
    print(f"[dmarc-ui] API: http://127.0.0.1:{port}/api/dmarc/status")


EXPLORER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Email Deliverability &amp; Brand-Protection Review</title>
  <style>
    :root {
      --bg:#0d1117; --panel:#161b22; --border:#30363d; --text:#e6edf3;
      --muted:#8b949e; --green:#3fb950; --red:#f85149; --amber:#d29922; --blue:#58a6ff;
    }
    * { box-sizing: border-box; }
    body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
    header { padding:1rem 1.25rem; border-bottom:1px solid var(--border); background:var(--panel);
      display:flex; flex-wrap:wrap; gap:1rem; align-items:center; justify-content:space-between; position:sticky; top:0; }
    h1 { margin:0; font-size:1.1rem; font-weight:600; }
    .meta, .nav a { color:var(--muted); font-size:0.85rem; }
    .nav { display:flex; gap:0.75rem; }
    .nav a { color:var(--blue); text-decoration:none; }
    main { max-width:1100px; margin:0 auto; padding:1rem 1.25rem 3rem; }
    .row { display:flex; gap:0.5rem; flex-wrap:wrap; margin:1rem 0; }
    input, button { background:#0d1117; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:0.45rem 0.7rem; }
    button { background:#1f6feb; border-color:#1f6feb; cursor:pointer; }
    button.secondary { background:var(--panel); color:var(--blue); }
    .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:0.75rem; }
    .card { background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:0.85rem; }
    .card b { display:block; font-size:1.3rem; }
    table { width:100%; border-collapse:collapse; font-size:0.85rem; margin-top:0.5rem; }
    th, td { border-bottom:1px solid var(--border); text-align:left; padding:0.35rem 0.4rem; vertical-align:top; }
    h2 { font-size:1rem; margin:1.4rem 0 0.4rem; }
    .bar { height:10px; background:#21262d; border-radius:6px; overflow:hidden; display:flex; }
    .bar span.ok { background:var(--green); }
    .bar span.bad { background:var(--red); }
    pre.disc { white-space:pre-wrap; color:var(--muted); font-size:0.75rem; border-top:1px solid var(--border); padding-top:1rem; }
    .warn { color:var(--amber); }
    .empty { color:var(--muted); font-style:italic; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Email Deliverability &amp; Brand-Protection Review</h1>
      <div class="meta" id="meta">Observational DNS / SPF / DKIM / DMARC report — not an email-security product</div>
    </div>
    <nav class="nav">
      <a href="/dmarc">DMARC</a>
      <a href="/monetize">Monetize</a>
      <a href="/monitor">Monitor</a>
    </nav>
  </header>
  <main>
    <div class="row">
      <input id="domain" placeholder="example.com.au" size="36"/>
      <button id="check">Run DNS / SPF / DKIM</button>
      <button id="report" class="secondary">Generate review</button>
    </div>
    <div class="cards" id="cards"></div>
    <h2>DNS</h2><div id="dns"></div>
    <h2>SPF</h2><div id="spf"></div>
    <h2>DKIM</h2><div id="dkim"></div>
    <h2>Aggregate sources</h2><div id="agg"></div>
    <h2>Inbox placement</h2><div id="inbox"></div>
    <h2>Forensic (RUF)</h2><div id="ruf"></div>
    <pre class="disc" id="disc"></pre>
  </main>
  <script>
    /*BOOT*/
    const DISCLAIMER = /*DISCLAIMER*/;
    const domainEl = document.getElementById("domain");
    function table(rows, keys) {
      if (!rows || !rows.length) return '<p class="empty">No rows in this window.</p>';
      let h = "<table><thead><tr>" + keys.map(k => "<th>"+k+"</th>").join("") + "</tr></thead><tbody>";
      for (const r of rows.slice(0, 40)) {
        h += "<tr>" + keys.map(k => "<td>"+String(r[k] ?? "")+"</td>").join("") + "</tr>";
      }
      return h + "</tbody></table>";
    }
    function render(state) {
      domainEl.value = state.domain || domainEl.value;
      document.getElementById("meta").textContent = (state.title || "") + " · " + (state.generated_at || "");
      const agg = state.aggregate || {};
      const rate = Math.round((agg.pass_rate || 0) * 1000) / 10;
      document.getElementById("cards").innerHTML = [
        ["Pass rate", (rate||0) + "%"],
        ["Messages", agg.message_count || 0],
        ["DNS rows", (state.dns||[]).length],
        ["DKIM rows", (state.dkim||[]).length],
        ["Inbox probes", (state.inbox||[]).length],
        ["Inventory tools", ((state.inventory||{}).tools||[]).length],
      ].map(([l,v]) => `<div class="card"><span class="meta">${l}</span><b>${v}</b></div>`).join("");
      document.getElementById("dns").innerHTML = table(state.dns, ["record_type","value","ttl"]);
      const spf = (state.spf && state.spf[0]) || state.spf || {};
      document.getElementById("spf").innerHTML = `<pre>${JSON.stringify(spf, null, 2)}</pre>`;
      document.getElementById("dkim").innerHTML = table(state.dkim, ["selector","public_key_length","warnings"]);
      const orgs = agg.by_org || [];
      document.getElementById("agg").innerHTML = orgs.map(o => {
        const tot = o.count || 1;
        const ok = Math.round(100 * (o.pass_count||0) / tot);
        return `<div>${o.source_org} (${o.count})<div class="bar"><span class="ok" style="width:${ok}%"></span><span class="bad" style="width:${100-ok}%"></span></div></div>`;
      }).join("") || '<p class="empty">Ingest RUA fixtures (`dmarc ingest pull --fixtures`) to populate this chart.</p>';
      document.getElementById("inbox").innerHTML = table(state.inbox, ["provider","seed_account","placement","sent_at"]);
      document.getElementById("ruf").innerHTML = table(state.forensic, ["source_ip","from_address","subject","dkim_result"]);
      document.getElementById("disc").textContent = state.disclaimer || DISCLAIMER || "";
    }
    async function load() {
      if (EMBEDDED) { render(EMBEDDED); return; }
      const d = domainEl.value || "example.com.au";
      const res = await fetch("/api/dmarc/status?domain=" + encodeURIComponent(d));
      render(await res.json());
    }
    document.getElementById("check").onclick = async () => {
      const d = domainEl.value.trim();
      if (!d) return;
      const res = await fetch("/api/dmarc/check", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({domain:d})});
      await res.json();
      await load();
    };
    document.getElementById("report").onclick = async () => {
      const d = domainEl.value.trim() || "example.com.au";
      const res = await fetch("/api/dmarc/report", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({domain:d, live:false})});
      const data = await res.json();
      alert("Wrote " + (data.markdown_path || "report"));
    };
    load();
  </script>
</body>
</html>
"""
