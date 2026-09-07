"""Tape-to-cloud public hub — 16 modules, six layers, sample reports."""

from __future__ import annotations

import html
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.tape_to_cloud_report_html import render_detailed_report
from tape_to_cloud.catalog import (
    CURSOR_RULES,
    DISCOVERY_DOCS,
    LAYER_CATALOG,
    LAYERS,
    MODULE_CATALOG,
    MODULES,
    ROOT,
    catalog_snapshot,
    resolved_discovery_doc,
)
from tape_to_cloud.catalog import (
    discovery_dir as _discovery_dir,
)
from tape_to_cloud.sample_reports import CITATIONS, get_report, list_reports

CROSS_CUTTING = LAYERS


def _repo_root() -> Path:
    return ROOT


def _forum_watcher_root() -> Path:
    return _repo_root() / "forum-watcher"


def _latest_discovery_markdown() -> dict[str, Any] | None:
    discoveries = _forum_watcher_root() / "discoveries"
    if not discoveries.is_dir():
        return None
    files = sorted(discoveries.glob("*.md"), reverse=True)
    if not files:
        return None
    latest = files[0]
    return {
        "path": str(latest.relative_to(_repo_root())),
        "name": latest.name,
        "modified_utc": datetime.fromtimestamp(latest.stat().st_mtime, tz=UTC).isoformat(),
        "size_bytes": latest.stat().st_size,
    }


def _load_seen_count() -> int:
    seen_path = _forum_watcher_root() / "state" / "seen.json"
    if not seen_path.is_file():
        return 0
    try:
        data = json.loads(seen_path.read_text(encoding="utf-8"))
        return len(data) if isinstance(data, list) else 0
    except (json.JSONDecodeError, OSError):
        return 0


def build_hub_state() -> dict[str, Any]:
    """JSON snapshot for /api/tape-to-cloud/status."""
    root = _repo_root()
    discovery = _discovery_dir()
    fw = _forum_watcher_root()
    sources_path = fw / "sources.yaml"
    catalog = catalog_snapshot()
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "product": "tape-to-cloud",
        "focus": "tape-to-cloud-only",
        "modules": list(MODULES),
        "module_count": len(MODULES),
        "layers": list(LAYERS),
        "layer_count": len(LAYERS),
        "catalog": catalog,
        "sample_reports": list_reports(),
        "discovery_docs": [
            {
                "file": name,
                "label": label,
                "path": str((discovery / name).relative_to(root)),
                "href": f"/tape-to-cloud/docs/{name}",
                "exists": (discovery / name).is_file(),
            }
            for name, label in DISCOVERY_DOCS
        ],
        "cursor_rules": [
            {
                "file": name,
                "path": str((root / ".cursor" / "rules" / name).relative_to(root)),
                "exists": (root / ".cursor" / "rules" / name).is_file(),
            }
            for name in CURSOR_RULES
        ],
        "packages": {
            "tape_to_cloud_ingest": (root / "tape_to_cloud" / "ingest.py").is_file(),
            "tape_to_cloud_monetize": (root / "tape_to_cloud" / "monetize").is_dir(),
            "forum_watcher": fw.is_dir(),
        },
        "forum_watcher": {
            "sources_configured": sources_path.is_file(),
            "seen_url_count": _load_seen_count(),
            "latest_discovery": _latest_discovery_markdown(),
            "workflow": ".github/workflows/forum-watcher.yml",
        },
        "cli": {
            "ingest": "python -m tape_to_cloud ingest PATH --matter MATTER",
            "restore": "python -m tape_to_cloud restore JOB_ID DEST",
            "verify": "python -m tape_to_cloud verify JOB_ID",
            "status": "python -m tape_to_cloud status",
            "report": "python -m tape_to_cloud report audit",
            "list": "python -m tape_to_cloud list",
            "ew_tool_ingest": "python3 ew_tool.py --tape-ingest PATH --tape-matter MATTER",
            "tape_monetize_cli": "python -m tape_to_cloud.monetize",
            "forum_watcher": "cd forum-watcher && python scripts/watch.py",
            "hub": "python3 ew_tool.py --monitor",
        },
        "web_routes": {
            "home": "/",
            "hub": "/tape-to-cloud",
            "modules": "/tape-to-cloud/modules",
            "layers": "/tape-to-cloud/layers",
            "jobs": "/tape-to-cloud/jobs",
            "reports": "/tape-to-cloud/reports",
            "job_pack": "/tape-to-cloud/reports/job-pack",
            "validation": "/tape-to-cloud/validation",
            "api": "/api/tape-to-cloud/status",
            "api_jobs": "/api/tape-to-cloud/jobs",
            "api_reports": "/api/tape-to-cloud/reports",
            "api_validation": "/api/tape-to-cloud/validation",
        },
        "honesty": {
            "working": "disk ingest of real file bytes with pre/post SHA-256, CoC, restore, verify, optional WORM, stdlib .eml/.mbox",
            "not_working": "LTO robotics, KMIP clusters, NetBackup/TSM, PST/NSF, SeaweedFS over the network",
        },
        "live_jobs": _live_jobs_snapshot(),
    }


def _live_jobs_snapshot() -> dict[str, Any]:
    from tape_to_cloud.ingest import default_store
    from tape_to_cloud.jobs import list_jobs

    jobs = list_jobs()
    return {"count": len(jobs), "store": str(default_store()), "jobs": jobs[:50]}


def _css() -> str:
    return """
    :root { --bg:#0d1117; --card:#161b22; --border:#30363d; --text:#e6edf3; --muted:#8b949e;
            --accent:#58a6ff; --green:#3fb950; --amber:#d29922; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
    header { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem;
             padding:1rem 1.25rem; border-bottom:1px solid var(--border); flex-wrap:wrap; }
    h1 { margin:0; font-size:1.25rem; }
    .nav a { color:var(--accent); margin-left:0.85rem; text-decoration:none; font-size:0.9rem; }
    .nav a:hover { text-decoration:underline; }
    main { padding:1.25rem; max-width:1180px; margin:0 auto; }
    section { background:var(--card); border:1px solid var(--border); border-radius:8px;
              padding:1rem 1.1rem; margin-bottom:1rem; }
    h2 { margin:0 0 0.75rem; font-size:1.05rem; }
    h3 { margin:0.2rem 0 0.4rem; font-size:0.95rem; }
    table { width:100%; border-collapse:collapse; font-size:0.88rem; }
    th, td { text-align:left; padding:0.45rem 0.5rem; border-bottom:1px solid var(--border); vertical-align:top; }
    .muted { color:var(--muted); font-size:0.85rem; }
    .ok { color:var(--green); }
    .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:0.75rem; }
    .card { display:block; background:var(--bg); border:1px solid var(--border); border-radius:8px;
            padding:0.85rem; color:inherit; text-decoration:none; min-height:8.5rem; }
    .card:hover { border-color:var(--accent); }
    .card p { display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }
    .card code { color:var(--accent); font-size:0.78rem; }
    .pill { display:inline-block; font-size:0.72rem; color:var(--amber); border:1px solid var(--amber);
            border-radius:999px; padding:0.05rem 0.45rem; margin-bottom:0.35rem; }
    .kpis { display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:0.6rem; margin:0.8rem 0; }
    .kpi { background:var(--bg); border:1px solid var(--border); border-radius:8px; padding:0.65rem; }
    .kpi-label { color:var(--muted); font-size:0.72rem; text-transform:uppercase; letter-spacing:0.03em; }
    .kpi-value { font-size:1.05rem; font-weight:600; margin-top:0.2rem; word-break:break-word; }
    .layer-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:0.65rem; }
    .layer-card { background:var(--bg); border:1px solid var(--border); border-radius:8px; padding:0.75rem; }
    .layer-card ul { margin:0.4rem 0 0; padding-left:1.1rem; font-size:0.82rem; }
    tr.risk-high { background:rgba(248,81,73,0.12); }
    tr.risk-mid { background:rgba(210,153,34,0.10); }
    table.kv th { width:32%; color:var(--muted); }
    ol.coc { font-size:0.88rem; }
    details { margin-top:0.5rem; }
    caption { text-align:left; color:var(--muted); padding:0.3rem 0; }
    pre { background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:0.75rem;
          overflow:auto; font-size:0.75rem; max-height:32rem; }
    a { color:var(--accent); }
    """


def _shell(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{_css()}</style>
</head>
<body>
  <header>
    <div>
      <h1>Tape-to-Cloud</h1>
      <div class="muted">Source-agnostic · target-agnostic · 16 modules · 6 layers · sample reports</div>
    </div>
    <nav class="nav">
      <a href="/tape-to-cloud">Home</a>
      <a href="/tape-to-cloud/modules">Modules</a>
      <a href="/tape-to-cloud/layers">Layers</a>
      <a href="/tape-to-cloud/jobs">Live jobs</a>
      <a href="/tape-to-cloud/reports">Reports</a>
      <a href="/tape-to-cloud/reports/job-pack">Job pack</a>
      <a href="/tape-to-cloud/validation">Validation</a>
      <a href="/api/tape-to-cloud/status">API</a>
    </nav>
  </header>
  <main>{body}</main>
</body>
</html>"""


def render_hub_html() -> str:
    state = build_hub_state()
    cards = "\n".join(
        f'<a class="card" href="/tape-to-cloud/modules/{html.escape(m["id"])}">'
        f'<div class="pill">sample ready</div>'
        f"<h3>{html.escape(m['menu'])}</h3>"
        f"<code>{html.escape(m['id'])}</code>"
        f'<p class="muted">{html.escape(m["deliverable"])}</p></a>'
        for m in state["catalog"]["modules"]
    )
    layer_cards = "\n".join(
        f'<a class="card" href="/tape-to-cloud/layers#{html.escape(layer["id"])}">'
        f"<h3>{html.escape(layer['title'])}</h3>"
        f"<code>{html.escape(layer['id'])}</code>"
        f'<p class="muted">{html.escape(layer["deliverable"])}</p></a>'
        for layer in state["catalog"]["layers"]
    )
    docs_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(d['label'])}</td>"
        f'<td><a href="{html.escape(d["href"])}"><code>{html.escape(d["file"])}</code></a></td>'
        f"<td>{'yes' if d['exists'] else 'missing'}</td></tr>"
        for d in state["discovery_docs"]
    )
    report_rows = "\n".join(
        "<tr>"
        f"<td><code>{html.escape(r['report_id'])}</code></td>"
        f"<td>{html.escape(r['menu'])}</td>"
        f'<td><a href="{html.escape(r["href"])}">HTML</a> · '
        f'<a href="{html.escape(r["json"])}">JSON</a></td></tr>'
        for r in state["sample_reports"]
    )
    targets = ", ".join(html.escape(t) for t in state["catalog"]["targets"])
    latest = state["forum_watcher"]["latest_discovery"]
    latest_line = (
        f'<p class="muted">Latest forum discovery: <code>{html.escape(latest["path"])}</code></p>'
        if latest
        else '<p class="muted">No forum-watcher discoveries yet.</p>'
    )
    citations = "".join(
        f'<li><a href="{html.escape(c["url"])}">{html.escape(c["title"])}</a> — {html.escape(c["fields"])}</li>'
        for c in CITATIONS
    )
    from engine.tape_to_cloud_reports import list_report_summaries, validate_intactness
    from tape_to_cloud.jobs import list_jobs

    intact = validate_intactness()
    intact_label = "INTACT" if intact["ok"] else "FAILED"
    intact_class = "ok" if intact["ok"] else "bad"
    intact_rows = "\n".join(
        "<tr>"
        f'<td><a href="{html.escape(r["href"])}"><code>{html.escape(r["id"])}</code></a></td>'
        f"<td>{html.escape(r['kind'])}</td><td>{html.escape(r['title'])}</td>"
        f"<td>{'verified' if r['hash_verified'] else 'MISMATCH'}</td></tr>"
        for r in list_report_summaries()
    )
    live = list_jobs()
    live_rows = (
        "\n".join(
            "<tr>"
            f'<td><a href="{html.escape(str(j["href"]), quote=True)}">'
            f"<code>{html.escape(str(j['id']))}</code></a></td>"
            f"<td>{html.escape(str(j['object_count']))}</td>"
            f"<td>{html.escape(str(j['bytes']))}</td>"
            f"<td>{html.escape(str(j['status']))}</td>"
            f"<td><code>{html.escape((j.get('canonical_sha256') or '')[:16])}…</code></td></tr>"
            for j in live
        )
        or "<tr><td colspan='5'>No live jobs yet. Run <code>python -m tape_to_cloud ingest PATH</code></td></tr>"
    )
    body = f"""
    <section>
      <h2>Public demo</h2>
      <p>Vendor-agnostic tape-to-cloud migration: LTO-1 through LTO-10, mainframe 3592/T10000,
         backup-app formats (TSM / NetBackup / Backup Exec / …), any S3-compatible target
         (SeaweedFS on-prem default). Every module calls the six cross-cutting layers.</p>
      <p class="ok">Sample job <code>{html.escape(state["catalog"]["sample_job_id"])}</code>
         for {html.escape(state["catalog"]["sample_customer"])} — 16 detailed module reports + combined job pack.</p>
      {latest_line}
      <p class="muted">Targets: {targets}</p>
      <p>Intactness: <strong class="{intact_class}">{intact_label}</strong>
         · 6 cross-cutting layers on every module.</p>
      <p>Every report calls <code>tape_to_cloud.layers.apply_layers</code>
         (SHA-256 sidecar, KMIP refuse, license-or-wrap readers, WORM stop-and-ask).</p>
      <pre>{html.escape(state["cli"]["ingest"])}
{html.escape(state["cli"]["report"])}
{html.escape(state["cli"]["list"])}</pre>
      <p class="muted">{html.escape(state["honesty"]["working"])}. Not in this MVP: {html.escape(state["honesty"]["not_working"])}.</p>
    </section>
    <section>
      <h2>Live ingest jobs (real bytes)</h2>
      <p class="muted">SHA-256 of actual file contents. CLI: <code>python -m tape_to_cloud ingest PATH --matter MATTER</code></p>
      <table><thead><tr><th>Job</th><th>Objects</th><th>Bytes</th><th>Status</th><th>SHA-256</th></tr></thead>
      <tbody>{live_rows}</tbody></table>
    </section>
    <section>
      <h2>16 modules</h2>
      <div class="grid">{cards}</div>
    </section>
    <section>
      <h2>Six cross-cutting layers</h2>
      <div class="grid">{layer_cards}</div>
    </section>
    <section>
      <h2>Sample reports</h2>
      <table><thead><tr><th>Report ID</th><th>Menu</th><th>Open</th></tr></thead>
      <tbody>{report_rows}</tbody></table>
    </section>
    <section>
      <h2>SHA-256 intactness fixtures</h2>
      <p class="muted">Vendor-shaped demo packages (not live tapes). Validation: <a href="/tape-to-cloud/validation">/tape-to-cloud/validation</a></p>
      <table><thead><tr><th>ID</th><th>Kind</th><th>Title</th><th>Hash</th></tr></thead>
      <tbody>{intact_rows}</tbody></table>
    </section>
    <section>
      <h2>Discovery docs</h2>
      <table><thead><tr><th>Doc</th><th>Public path</th><th>On disk</th></tr></thead>
      <tbody>{docs_rows}</tbody></table>
    </section>
    <section>
      <h2>Research basis (not an affiliation)</h2>
      <ul class="citations">{citations}</ul>
    </section>
    """
    return _shell("Tape-to-Cloud Hub", body)


def render_modules_index_html() -> str:
    rows = "\n".join(
        "<tr>"
        f'<td><a href="/tape-to-cloud/modules/{html.escape(mid)}"><code>{html.escape(mid)}</code></a></td>'
        f"<td>{html.escape(spec['menu'])}</td>"
        f"<td>{html.escape(spec['deliverable'])}</td>"
        f'<td><a href="/tape-to-cloud/reports/{html.escape(mid)}">report</a></td></tr>'
        for mid, spec in MODULE_CATALOG.items()
    )
    body = f"""
    <section>
      <h2>All modules</h2>
      <table><thead><tr><th>ID</th><th>Menu</th><th>Deliverable</th><th>Sample</th></tr></thead>
      <tbody>{rows}</tbody></table>
    </section>
    """
    return _shell("Tape-to-Cloud modules", body)


def render_module_html(module_id: str) -> str:
    spec = MODULE_CATALOG[module_id]
    report = get_report(module_id)
    detail = render_detailed_report(report, f"/api/tape-to-cloud/reports/{module_id}")
    body = f"""
    <section>
      <p class="pill">module</p>
      <h2>{html.escape(spec["menu"])}</h2>
      <p><code>{html.escape(module_id)}</code></p>
      <p>{html.escape(spec["deliverable"])}</p>
      <p class="muted">Sources: {html.escape(spec["sources"])}</p>
    </section>
    {detail}
    """
    return _shell(f"{spec['menu']} · tape-to-cloud", body)


def render_layers_html() -> str:
    intro = """
    <section>
      <h2>Engine</h2>
      <p>Every sample report is produced by <code>tape_to_cloud.layers.apply_layers</code>.
         Order: rescue → KMIP → format readers → integrity (SHA-256) → WORM → eDiscovery.
         Missing KMIP key, invented TSM/NetBackup parsers, and crypto bypass are hard refusals.
         WORM vs GDPR erasure is stop-and-ask.</p>
      <pre>python -m tape_to_cloud report audit
python -m tape_to_cloud list</pre>
    </section>
    """
    blocks = [intro]
    for lid in LAYERS:
        spec = LAYER_CATALOG[lid]
        blocks.append(
            f'<section id="{html.escape(lid)}"><h2>{html.escape(spec["title"])}</h2>'
            f"<p><code>{html.escape(lid)}</code></p>"
            f"<p>{html.escape(spec['deliverable'])}</p>"
            f'<p class="muted">Required on every module — not an extra brochure item.</p></section>'
        )
    return _shell("Tape-to-Cloud layers", "\n".join(blocks))


def render_reports_index_html() -> str:
    from engine.tape_to_cloud_reports import list_report_summaries

    rows = "\n".join(
        "<tr>"
        f"<td><code>{html.escape(r['report_id'])}</code></td>"
        f"<td>{html.escape(r['module'])}</td>"
        f"<td>{html.escape(r['menu'])}</td>"
        f'<td><a href="{html.escape(r["href"])}">HTML</a> · '
        f'<a href="{html.escape(r["json"])}">JSON</a></td></tr>'
        for r in list_reports()
    )
    intact_rows = "\n".join(
        "<tr>"
        f'<td><a href="{html.escape(r["href"])}"><code>{html.escape(r["id"])}</code></a></td>'
        f"<td>{html.escape(r['kind'])}</td>"
        f"<td>{html.escape(r['title'])}</td>"
        f"<td>{'verified' if r['hash_verified'] else 'MISMATCH'}</td></tr>"
        for r in list_report_summaries()
    )
    body = f"""
    <section>
      <h2>Sample reports</h2>
      <p class="muted">Synthetic demo job <code>JOB-DEMO-ACME-LTO</code>. Not a customer record.</p>
      <p><a href="/tape-to-cloud/reports/job-pack">Open combined job pack</a></p>
      <table><thead><tr><th>Report ID</th><th>Module</th><th>Menu</th><th>Open</th></tr></thead>
      <tbody>{rows}</tbody></table>
    </section>
    <section>
      <h2>SHA-256 intactness fixtures</h2>
      <p class="muted">Vendor-shaped demo packages. Canonical JSON hashed with SHA-256.</p>
      <table><thead><tr><th>ID</th><th>Kind</th><th>Title</th><th>Hash</th></tr></thead>
      <tbody>{intact_rows}</tbody></table>
    </section>
    """
    return _shell("Tape-to-Cloud sample reports", body)


def render_report_html(report_key: str) -> str:
    report = get_report(report_key)
    title = f"{report['report_id']} · sample report"
    detail = render_detailed_report(report, f"/api/tape-to-cloud/reports/{report_key}")
    return _shell(title, detail)


def render_doc_text(name: str) -> tuple[int, dict[str, str], bytes] | None:
    path = resolved_discovery_doc(name)
    if path is None:
        return None
    if not path.is_file():
        body = f"missing: {name}\n".encode()
        return 404, {"Content-Type": "text/plain; charset=utf-8"}, body
    text = path.read_text(encoding="utf-8")
    escaped = html.escape(text)
    page = _shell(
        name,
        f"<section><h2>{html.escape(name)}</h2><pre>{escaped}</pre></section>",
    )
    return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, page.encode("utf-8")


def _json_bytes(payload: Any) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload, indent=2, default=str).encode("utf-8")
    return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body


def _html_bytes(page: str) -> tuple[int, dict[str, str], bytes]:
    return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, page.encode("utf-8")


def _not_found(msg: str) -> tuple[int, dict[str, str], bytes]:
    return 404, {"Content-Type": "text/plain; charset=utf-8"}, msg.encode("utf-8")


def _dispatch_live_jobs(path: str) -> tuple[int, dict[str, str], bytes] | None:
    from tape_to_cloud.jobs import list_jobs, load_job

    html_hdr = {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}
    json_hdr = {"Content-Type": "application/json", "Cache-Control": "no-store"}
    if path == "/tape-to-cloud/jobs":
        rows = list_jobs()
        body_rows = (
            "\n".join(
                f"<tr><td><a href='{html.escape(str(j['href']), quote=True)}'><code>"
                f"{html.escape(str(j['id']))}</code></a></td>"
                f"<td>{html.escape(str(j['object_count']))}</td>"
                f"<td>{html.escape(str(j['bytes']))}</td>"
                f"<td>{html.escape(str(j['status']))}</td></tr>"
                for j in rows
            )
            or "<tr><td colspan='4'>No live jobs. Run python -m tape_to_cloud ingest PATH</td></tr>"
        )
        listing_page = _shell(
            "Live ingest jobs",
            "<section><h2>Live ingest jobs</h2>"
            "<table><thead><tr><th>Job</th><th>Objects</th><th>Bytes</th><th>Status</th></tr></thead>"
            f"<tbody>{body_rows}</tbody></table></section>",
        )
        return 200, html_hdr, listing_page.encode("utf-8")
    if path.startswith("/tape-to-cloud/jobs/"):
        job_id = path.rsplit("/", 1)[-1]
        job = load_job(job_id)
        if job is None:
            return 404, html_hdr, b"<html><body>unknown job</body></html>"
        safe_id = html.escape(job_id)
        payload = html.escape(json.dumps(job, indent=2, default=str))
        html_page = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>"
            f"{safe_id}</title></head>"
            "<body style='font-family:sans-serif;background:#0d1117;color:#e6edf3'>"
            "<p><a href='/tape-to-cloud/jobs'>All live jobs</a></p>"
            f"<h1>Live job {safe_id}</h1>"
            f"<p>sample={html.escape(str(job.get('sample')))} (must be false) · "
            f"objects={html.escape(str(job.get('object_count')))} · "
            f"SHA-256 {html.escape(str(job.get('canonical_sha256')))}</p>"
            f"<pre>{payload}</pre></body></html>"
        )
        return 200, html_hdr, html_page.encode("utf-8")
    if path == "/api/tape-to-cloud/jobs":
        rows = list_jobs()
        return 200, json_hdr, json.dumps({"jobs": rows, "count": len(rows)}, indent=2).encode("utf-8")
    if path.startswith("/api/tape-to-cloud/jobs/"):
        job_id = path.rsplit("/", 1)[-1]
        job = load_job(job_id)
        if job is None:
            return 404, json_hdr, json.dumps({"error": "unknown_job", "id": job_id}).encode("utf-8")
        return 200, json_hdr, json.dumps(job, indent=2, default=str).encode("utf-8")
    return None


def _module_or_pack(key: str) -> bool:
    return key in MODULES or key == "job-pack"


def dispatch_tape_to_cloud(
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]] | None = None,
) -> tuple[int, dict[str, str], bytes] | None:
    from engine import tape_to_cloud_reports as intact_mod

    raw = path or "/"
    path = raw.rstrip("/") or "/"
    method = (method or "GET").upper()
    if method != "GET":
        return None

    job_hit = _dispatch_live_jobs(path)
    if job_hit is not None:
        return job_hit

    parts = [p for p in path.split("/") if p]
    if parts[:1] == ["tape-to-cloud"]:
        rest = parts[1:]
    elif path == "/":
        rest = []
    elif parts[:2] == ["api", "tape-to-cloud"]:
        rest = ["api", *parts[2:]]
    else:
        return None

    if rest == ["validation"]:
        return _html_bytes(intact_mod.render_validation_html())
    if rest[:1] == ["api"] and rest[1:] == ["validation"]:
        return _json_bytes(intact_mod.validate_intactness())

    kind = None
    if query and query.get("kind"):
        kind = query["kind"][0]

    if rest[:1] == ["api"]:
        api_rest = rest[1:]
        if api_rest == [] or api_rest == ["status"]:
            return _json_bytes(build_hub_state())
        if api_rest == ["modules"]:
            return _json_bytes(catalog_snapshot()["modules"])
        if len(api_rest) == 2 and api_rest[0] == "modules":
            mid = api_rest[1]
            if mid not in MODULE_CATALOG:
                return _not_found(f"unknown module: {mid}\n")
            return _json_bytes({"module": mid, **MODULE_CATALOG[mid], "report": get_report(mid)})
        if api_rest == ["layers"]:
            return _json_bytes(catalog_snapshot()["layers"])
        if api_rest == ["reports"]:
            rows = intact_mod.list_report_summaries(kind)
            return _json_bytes({"reports": rows, "count": len(rows)})
        if len(api_rest) == 2 and api_rest[0] == "reports":
            key = api_rest[1]
            if _module_or_pack(key):
                try:
                    return _json_bytes(get_report(key))
                except KeyError:
                    return _not_found(f"unknown report: {key}\n")
            fixture = intact_mod.get_report(key)
            if fixture is None:
                body = json.dumps({"error": "unknown_report", "id": key}).encode("utf-8")
                return 404, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body
            return _json_bytes(fixture)
        return _not_found("unknown tape-to-cloud API path\n")

    if rest == []:
        return _html_bytes(render_hub_html())
    if rest == ["modules"]:
        return _html_bytes(render_modules_index_html())
    if len(rest) == 2 and rest[0] == "modules":
        mid = rest[1]
        if mid not in MODULE_CATALOG:
            return _not_found(f"unknown module: {mid}\n")
        return _html_bytes(render_module_html(mid))
    if rest == ["layers"]:
        return _html_bytes(render_layers_html())
    if rest == ["reports"]:
        return _html_bytes(render_reports_index_html())
    if len(rest) == 2 and rest[0] == "reports":
        key = rest[1]
        if key.endswith(".json"):
            key = key[: -len(".json")]
            if _module_or_pack(key):
                try:
                    return _json_bytes(get_report(key))
                except KeyError:
                    return _not_found(f"unknown report: {key}\n")
            fixture = intact_mod.get_report(key)
            if fixture is None:
                return _not_found(f"unknown report: {key}\n")
            return _json_bytes(fixture)
        if _module_or_pack(key):
            try:
                return _html_bytes(render_report_html(key))
            except KeyError:
                return _not_found(f"unknown report: {key}\n")
        fixture = intact_mod.get_report(key)
        if fixture is None:
            return _not_found(f"unknown report: {key}\n")
        return _html_bytes(intact_mod.render_report_detail_html(fixture))
    if len(rest) == 2 and rest[0] == "docs":
        return render_doc_text(rest[1])
    report_hit = intact_mod.dispatch_report_routes(method, path, query)
    if report_hit is not None:
        return report_hit
    return _not_found("unknown tape-to-cloud path\n")


def serve_tape_to_cloud_http(handler: Any, method: str, path: str, query: Mapping[str, Sequence[str]]) -> bool:
    result = dispatch_tape_to_cloud(method, path, query)
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
