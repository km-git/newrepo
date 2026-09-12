"""HTTP API for tape-to-cloud platform."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from typing import Any

from tape_to_cloud.core.constants import CROSS_CUTTING_LAYERS, DEFAULT_DATA_DIR, MODULES
from tape_to_cloud.core.platform import PlatformContext
from tape_to_cloud.core.registry import list_modules, module_descriptions, run_job, submit_and_run


def _ctx() -> PlatformContext:
    data_dir = os.environ.get("EW_TTC_DATA_DIR", DEFAULT_DATA_DIR)
    return PlatformContext(data_dir)


def platform_status() -> dict[str, Any]:
    ctx = _ctx()
    return {
        "modules": list(MODULES),
        "module_count": len(MODULES),
        "cross_cutting_layers": list(CROSS_CUTTING_LAYERS),
        "module_descriptions": module_descriptions(),
        "jobs": ctx.jobs.stats(),
        "vault_objects": len(ctx.vault.list_objects()),
        "data_dir": str(ctx.data_dir),
    }


def handle_api(
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]],
    body: bytes = b"",
) -> tuple[int, dict[str, str], bytes] | None:
    path = path.rstrip("/") or "/"
    method = (method or "GET").upper()

    if path == "/api/tape-to-cloud/platform" and method == "GET":
        payload = json.dumps(platform_status(), indent=2, default=str).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, payload

    if path == "/api/tape-to-cloud/modules" and method == "GET":
        payload = json.dumps({"modules": list_modules()}, indent=2).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, payload

    if path == "/api/tape-to-cloud/jobs" and method == "GET":
        ctx = _ctx()
        module = (query.get("module") or [None])[0]
        limit = int((query.get("limit") or ["100"])[0])
        jobs = ctx.jobs.list_jobs(module=module, limit=limit)
        payload = json.dumps({"jobs": jobs}, indent=2, default=str).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, payload

    if path.startswith("/api/tape-to-cloud/jobs/") and method == "GET":
        job_id = path.split("/")[-1]
        ctx = _ctx()
        job = ctx.jobs.get_job(job_id)
        if job is None:
            return 404, {"Content-Type": "application/json"}, json.dumps({"error": "not found"}).encode()
        payload = json.dumps(job, indent=2, default=str).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, payload

    if path == "/api/tape-to-cloud/jobs" and method == "POST":
        try:
            data = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return 400, {"Content-Type": "application/json"}, json.dumps({"error": "invalid json"}).encode()
        module = data.get("module")
        params = data.get("params") or {}
        if not module:
            return 400, {"Content-Type": "application/json"}, json.dumps({"error": "module required"}).encode()
        ctx = _ctx()
        try:
            job = submit_and_run(ctx, module, params)
        except (ValueError, FileNotFoundError, PermissionError) as exc:
            return 400, {"Content-Type": "application/json"}, json.dumps({"error": str(exc)}).encode()
        payload = json.dumps(job, indent=2, default=str).encode("utf-8")
        return 201, {"Content-Type": "application/json", "Cache-Control": "no-store"}, payload

    if path.startswith("/api/tape-to-cloud/jobs/") and path.endswith("/run") and method == "POST":
        job_id = path.removeprefix("/api/tape-to-cloud/jobs/").removesuffix("/run")
        ctx = _ctx()
        try:
            job = run_job(ctx, job_id)
        except ValueError as exc:
            return 404, {"Content-Type": "application/json"}, json.dumps({"error": str(exc)}).encode()
        payload = json.dumps(job, indent=2, default=str).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, payload

    return None


_PLATFORM_CSS = """
    :root {
      --bg:#0d1117; --card:#161b22; --border:#30363d;
      --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --green:#3fb950;
    }
    * { box-sizing:border-box; }
    body {
      margin:0; font-family:ui-sans-serif,system-ui,sans-serif;
      background:var(--bg); color:var(--text);
    }
    header {
      display:flex; justify-content:space-between; align-items:center;
      padding:1rem 1.25rem; border-bottom:1px solid var(--border);
    }
    h1 { margin:0; font-size:1.25rem; }
    .nav a { color:var(--accent); margin-left:1rem; text-decoration:none; }
    main { padding:1.25rem; max-width:1200px; margin:0 auto; }
    section {
      background:var(--card); border:1px solid var(--border);
      border-radius:8px; padding:1rem; margin-bottom:1rem;
    }
    h2 { margin:0 0 0.75rem; font-size:1rem; }
    .grid {
      display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
      gap:0.75rem;
    }
    .card {
      background:var(--bg); border:1px solid var(--border);
      border-radius:6px; padding:0.75rem;
    }
    .muted { color:var(--muted); font-size:0.85rem; }
    button {
      background:var(--accent); color:#fff; border:0; border-radius:4px;
      padding:0.4rem 0.7rem; cursor:pointer; margin-top:0.5rem;
    }
    pre {
      background:var(--bg); border:1px solid var(--border); border-radius:6px;
      padding:0.75rem; overflow:auto; font-size:0.75rem; max-height:300px;
    }
    .ok { color:var(--green); }
    #job-result { margin-top:0.75rem; }
"""


def render_platform_html() -> str:
    status = platform_status()
    jobs_json = json.dumps(_ctx().jobs.list_jobs(limit=20), indent=2, default=str)
    layers = ", ".join(CROSS_CUTTING_LAYERS)
    job_total = status["jobs"]["total"]
    vault_count = status["vault_objects"]
    data_dir = status["data_dir"]
    module_cards = "\n".join(
        f'<div class="card"><h3>{m["id"]}</h3><p class="muted">{m["description"]}</p>'
        f"<button onclick=\"submitJob('{m['id']}')\">Run sample</button></div>"
        for m in list_modules()
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tape-to-Cloud Platform</title>
  <style>{_PLATFORM_CSS}</style>
</head>
<body>
  <header>
    <div><h1>Tape-to-Cloud Platform</h1><div class="muted">16 modules · 6 layers · job API</div></div>
    <nav class="nav">
      <a href="/tape-to-cloud">Hub</a>
      <a href="/tape-to-cloud/platform">Platform</a>
      <a href="/monetize">Monetize</a>
      <a href="/monitor">Monitor</a>
    </nav>
  </header>
  <main>
    <section>
      <h2>Status</h2>
      <p>Jobs: <strong>{job_total}</strong> · Vault objects: <strong>{vault_count}</strong></p>
      <p class="muted">Layers: {layers}</p>
      <p class="ok">Data dir: <code>{data_dir}</code></p>
    </section>
    <section>
      <h2>Submit job</h2>
      <p class="muted">POST <code>/api/tape-to-cloud/jobs</code></p>
      <div id="job-result"></div>
    </section>
    <section>
      <h2>Modules</h2>
      <div class="grid">{module_cards}</div>
    </section>
    <section>
      <h2>Recent jobs</h2>
      <pre id="jobs">{jobs_json}</pre>
    </section>
  </main>
  <script>
    async function submitJob(module) {{
      const params = module === 'audit' ? {{format:'LTO-8'}} :
                     module === 'tape-vault' ? {{action:'list'}} :
                     module === 'vtl-cloud' ? {{backend:'seaweedfs'}} : {{}};
      const res = await fetch('/api/tape-to-cloud/jobs', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{module, params}})
      }});
      const data = await res.json();
      document.getElementById('job-result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
      const jobsRes = await fetch('/api/tape-to-cloud/jobs?limit=20');
      document.getElementById('jobs').textContent = JSON.stringify(await jobsRes.json(), null, 2);
    }}
  </script>
</body>
</html>"""


def dispatch_platform(
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]],
    body: bytes = b"",
) -> tuple[int, dict[str, str], bytes] | None:
    path = path.rstrip("/") or "/"
    api = handle_api(method, path, query, body)
    if api is not None:
        return api
    if method == "GET" and path == "/tape-to-cloud/platform":
        html = render_platform_html().encode("utf-8")
        return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, html
    return None
