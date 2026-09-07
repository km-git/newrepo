"""Tape-to-cloud operations hub — local Web UI for discovery docs and forum-watcher status."""

from __future__ import annotations

import html
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

MODULES = (
    "audit",
    "analytics",
    "vtl-cloud",
    "restore",
    "disk-ingest",
    "email-extract",
    "email-migrate",
    "tape-duplicate",
    "media-ingest",
    "tape-ops",
    "tape-saas",
    "tape-vault",
    "destroy",
    "llm-corpus",
    "ml-enrich",
    "monetize",
)

CROSS_CUTTING = (
    "integrity",
    "ediscovery",
    "kms-kmip",
    "worm",
    "format-readers",
    "media-rescue",
)

DISCOVERY_DOCS = (
    ("free-tool-inventory.md", "Free-tool inventory catalog"),
    ("forum-monitoring.md", "Forum watcher spec"),
    ("continuous-improvement-loop-prompt.md", "Improvement loop prompt"),
    ("tape-to-cloud-migration-blueprint.md", "Migration blueprint"),
    ("feature-completeness.md", "Feature completeness matrix"),
    ("cursor-prompt.md", "Cursor build prompt"),
    ("pyproject-dependencies.toml", "Dependency matrix reference"),
)

CURSOR_RULES = (
    "tape-to-cloud-build.mdc",
    "tape-to-cloud-improvement-loop.mdc",
    "tape-to-cloud-free-tool-inventory.mdc",
)


def _repo_root() -> Path:
    return ROOT


def _discovery_dir() -> Path:
    return _repo_root() / "discovery" / "tape-to-cloud"


def _forum_watcher_root() -> Path:
    return _repo_root() / "forum-watcher"


def _latest_discovery_markdown() -> dict[str, str] | None:
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

    platform: dict[str, Any] = {}
    try:
        from tape_to_cloud.web.api import platform_status

        platform = platform_status()
    except Exception:
        platform = {"error": "platform not loaded"}

    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "modules": list(MODULES),
        "module_count": len(MODULES),
        "platform": platform,
        "layers": list(CROSS_CUTTING),
        "layer_count": len(CROSS_CUTTING),
        "discovery_docs": [
            {
                "file": name,
                "label": label,
                "path": str((discovery / name).relative_to(root)),
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
            "ew_tool_ingest": "python3 ew_tool.py --tape-ingest PATH --tape-matter MATTER",
            "monetize_strategy": "python3 ew_tool.py --monetize",
            "tape_monetize_cli": "python -m tape_to_cloud.monetize",
            "forum_watcher": "cd forum-watcher && python scripts/watch.py",
        },
        "web_routes": {
            "hub": "/tape-to-cloud",
            "platform": "/tape-to-cloud/platform",
            "jobs": "/tape-to-cloud/jobs",
            "reports": "/tape-to-cloud/reports",
            "validation": "/tape-to-cloud/validation",
            "monitor": "/monitor",
            "monetize": "/monetize",
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


def render_hub_html() -> str:
    from engine.tape_to_cloud_reports import list_report_summaries, validate_intactness
    from tape_to_cloud.jobs import list_jobs

    state = build_hub_state()
    payload = json.dumps(state, indent=2)
    modules_html = "\n".join(f"<li><code>{m}</code></li>" for m in MODULES)
    layers_html = "\n".join(f"<li><code>{m}</code></li>" for m in CROSS_CUTTING)
    docs_rows = "\n".join(
        f"<tr><td>{d['label']}</td><td><code>{d['path']}</code></td><td>{'yes' if d['exists'] else 'missing'}</td></tr>"
        for d in state["discovery_docs"]
    )
    latest = state["forum_watcher"]["latest_discovery"]
    latest_line = (
        f"<p>Latest: <code>{latest['path']}</code> ({latest['modified_utc']})</p>"
        if latest
        else "<p>No discoveries markdown yet — run forum-watcher or wait for Monday cron.</p>"
    )
    intact = validate_intactness()
    intact_label = "INTACT" if intact["ok"] else "FAILED"
    intact_class = "ok" if intact["ok"] else "bad"
    report_rows = "\n".join(
        f"<tr><td><a href='{r['href']}'><code>{r['id']}</code></a></td>"
        f"<td>{r['kind']}</td><td>{r['title']}</td>"
        f"<td>{r['status']}</td>"
        f"<td>{'verified' if r['hash_verified'] else 'MISMATCH'}</td></tr>"
        for r in list_report_summaries()
    )
    live = list_jobs()
    live_rows = (
        "\n".join(
            f"<tr><td><a href='{html.escape(str(j['href']), quote=True)}'><code>"
            f"{html.escape(str(j['id']))}</code></a></td>"
            f"<td>{html.escape(str(j['object_count']))}</td>"
            f"<td>{html.escape(str(j['bytes']))}</td>"
            f"<td>{html.escape(str(j['status']))}</td>"
            f"<td><code>{html.escape((j.get('canonical_sha256') or '')[:16])}…</code></td></tr>"
            for j in live
        )
        or "<tr><td colspan='5'>No live jobs yet. Run <code>python -m tape_to_cloud ingest PATH</code></td></tr>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tape-to-Cloud Hub</title>
  <style>
    :root {{ --bg:#0d1117; --card:#161b22; --border:#30363d; --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --green:#3fb950; --red:#f85149; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }}
    header {{ display:flex; justify-content:space-between; align-items:center; padding:1rem 1.25rem; border-bottom:1px solid var(--border); }}
    h1 {{ margin:0; font-size:1.25rem; }}
    .nav a {{ color:var(--accent); margin-left:1rem; text-decoration:none; }}
    main {{ padding:1.25rem; max-width:1100px; margin:0 auto; }}
    section {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:1rem 1.1rem; margin-bottom:1rem; }}
    h2 {{ margin:0 0 0.75rem; font-size:1rem; }}
    table {{ width:100%; border-collapse:collapse; font-size:0.9rem; }}
    th, td {{ text-align:left; padding:0.45rem 0.5rem; border-bottom:1px solid var(--border); }}
    .muted {{ color:var(--muted); font-size:0.85rem; }}
    .modules {{ columns:3; font-size:0.85rem; }}
    .layers {{ columns:2; font-size:0.85rem; }}
    pre {{ background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:0.75rem; overflow:auto; font-size:0.75rem; }}
    .ok {{ color:var(--green); }}
    .bad {{ color:var(--red); }}
    a {{ color:var(--accent); }}
  </style>
</head>
<body>
  <header>
    <div><h1>Tape-to-Cloud Hub</h1><div class="muted">Live disk ingest · SHA-256 of real bytes · sample fixtures labeled separately</div></div>
    <nav class="nav">
      <a href="/monitor">Monitor</a>
      <a href="/monetize">Monetize</a>
      <a href="/tape-to-cloud/platform">Platform</a>
      <a href="/tape-to-cloud">Hub</a>
      <a href="/tape-to-cloud/jobs">Live jobs</a>
      <a href="/tape-to-cloud/reports">Sample reports</a>
      <a href="/tape-to-cloud/validation">Validation</a>
    </nav>
  </header>
  <main>
    <section>
      <h2>Status</h2>
      <p class="muted">Live JSON: <code>/api/tape-to-cloud/status</code> · Validation: <a href="/tape-to-cloud/validation">/tape-to-cloud/validation</a></p>
      <p>Forum watcher seen URLs: <strong>{state["forum_watcher"]["seen_url_count"]}</strong></p>
      {latest_line}

      <p class="ok">Packages: ingest={"yes" if state["packages"].get("tape_to_cloud_ingest") else "no"},
        tape_to_cloud.monetize={"yes" if state["packages"]["tape_to_cloud_monetize"] else "no"},
        forum-watcher={"yes" if state["packages"]["forum_watcher"] else "no"}</p>
      <p class="muted">{state["honesty"]["working"]}. Not in this MVP: {state["honesty"]["not_working"]}.</p>
      <p>Platform catalog jobs: <strong>{state.get("platform", {}).get("jobs", {}).get("total", 0)}</strong>
        · Vault objects: <strong>{state.get("platform", {}).get("vault_objects", 0)}</strong>
        · UI: <a href="/tape-to-cloud/platform">/tape-to-cloud/platform</a></p>
      <p>Intactness: <strong class="{intact_class}">{intact_label}</strong> ({intact["checks"]["sixteen_modules"] and intact["checks"]["six_layers"] and "16 modules + 6 layers on disk"})</p>
    </section>
    <section>
      <h2>Live ingest jobs (real bytes)</h2>
      <p class="muted">SHA-256 of actual file contents. CLI: <code>python -m tape_to_cloud ingest PATH --matter MATTER</code>
         · JSON: <code>/api/tape-to-cloud/jobs</code></p>
      <table><thead><tr><th>Job</th><th>Objects</th><th>Bytes</th><th>Status</th><th>Manifest</th></tr></thead>
      <tbody>{live_rows}</tbody></table>
    </section>
    <section>
      <h2>Sample detailed reports (fixtures, not live tapes)</h2>
      <p class="muted">SHA-256 of canonical JSON (MD5/SHA-1 refused). Full pages at <a href="/tape-to-cloud/reports">/tape-to-cloud/reports</a></p>
      <table><thead><tr><th>ID</th><th>Kind</th><th>Title</th><th>Status</th><th>Hash</th></tr></thead>
      <tbody>{report_rows}</tbody></table>
    </section>
    <section>
      <h2>16 modules</h2>
      <ul class="modules">{modules_html}</ul>
    </section>
    <section>
      <h2>6 cross-cutting layers</h2>
      <ul class="layers">{layers_html}</ul>
      <p class="muted">Not a 17th brochure SKU — every module must call these layers.</p>
    </section>
    <section>
      <h2>Discovery docs</h2>
      <table><thead><tr><th>Doc</th><th>Path</th><th>On disk</th></tr></thead><tbody>{docs_rows}</tbody></table>
    </section>
    <section>
      <h2>CLI quick start</h2>
      <pre>python -m tape_to_cloud ingest ./my-export --matter ACME-014 --worm-until 2033-12-31T00:00:00+00:00
python -m tape_to_cloud verify JOB_ID
python -m tape_to_cloud restore JOB_ID ./restored
python3 ew_tool.py --monitor          # this Web UI (port 8765)
python3 ew_tool.py --tape-ingest PATH # same ingest via ew_tool
python -m tape_to_cloud.monetize      # license / royalty CLI</pre>
    </section>
    <section>
      <h2>API payload</h2>
      <pre id="json">{payload}</pre>
    </section>
  </main>
</body>
</html>"""


def dispatch_tape_to_cloud(
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]] | None = None,
    body: bytes = b"",
) -> tuple[int, dict[str, str], bytes] | None:
    from engine.tape_to_cloud_reports import dispatch_report_routes
    from tape_to_cloud.web.api import dispatch_platform, handle_api

    path = path.rstrip("/") or "/"
    method = (method or "GET").upper()
    # Live ingest owns GET /tape-to-cloud/jobs and GET /api/tape-to-cloud/jobs.
    # Platform catalog is /tape-to-cloud/platform plus POST job APIs.
    if method == "GET" and path in (
        "/tape-to-cloud/platform",
        "/api/tape-to-cloud/platform",
        "/api/tape-to-cloud/modules",
    ):
        plat = dispatch_platform(method, path, query or {}, body)
        if plat is not None:
            return plat
    if method != "GET":
        api = handle_api(method, path, query or {}, body)
        if api is not None:
            return api
        return None
    report_hit = dispatch_report_routes(method, path, query)
    if report_hit is not None:
        return report_hit
    job_hit = _dispatch_live_jobs(path)
    if job_hit is not None:
        return job_hit
    if path in ("/tape-to-cloud", "/tape-to-cloud/"):
        page = render_hub_html().encode("utf-8")
        return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, page
    if path == "/api/tape-to-cloud/status":
        payload = json.dumps(build_hub_state(), indent=2, default=str).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, payload
    return None



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
        listing_page = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Live jobs</title></head>"
            "<body style='font-family:sans-serif;background:#0d1117;color:#e6edf3'>"
            "<p><a href='/tape-to-cloud'>Hub</a></p><h1>Live ingest jobs</h1>"
            "<table border='1' cellpadding='6'><tr><th>Job</th><th>Objects</th>"
            f"<th>Bytes</th><th>Status</th></tr>{body_rows}</table></body></html>"
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
        return 200, json_hdr, json.dumps(job, indent=2).encode("utf-8")
    return None


def serve_tape_to_cloud_http(
    handler: Any,
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]],
    body: bytes = b"",
) -> bool:
    result = dispatch_tape_to_cloud(method, path, query, body)
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
