"""Tape-to-cloud operations hub — local Web UI for discovery docs and forum-watcher status."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

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


def _latest_discovery_markdown() -> Optional[dict[str, str]]:
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
        "modified_utc": datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc).isoformat(),
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

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "modules": list(MODULES),
        "module_count": len(MODULES),
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
            "monetize_strategy": "python3 ew_tool.py --monetize",
            "tape_monetize_cli": "python -m tape_to_cloud.monetize",
            "forum_watcher": "cd forum-watcher && python scripts/watch.py",
        },
        "web_routes": {
            "hub": "/tape-to-cloud",
            "monitor": "/monitor",
            "monetize": "/monetize",
            "api": "/api/tape-to-cloud/status",
        },
    }


def render_hub_html() -> str:
    state = build_hub_state()
    payload = json.dumps(state, indent=2)
    modules_html = "\n".join(f"<li><code>{m}</code></li>" for m in MODULES)
    docs_rows = "\n".join(
        f"<tr><td>{d['label']}</td><td><code>{d['path']}</code></td>"
        f"<td>{'yes' if d['exists'] else 'missing'}</td></tr>"
        for d in state["discovery_docs"]
    )
    latest = state["forum_watcher"]["latest_discovery"]
    latest_line = (
        f"<p>Latest: <code>{latest['path']}</code> ({latest['modified_utc']})</p>"
        if latest
        else "<p>No discoveries markdown yet — run forum-watcher or wait for Monday cron.</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tape-to-Cloud Hub</title>
  <style>
    :root {{ --bg:#0d1117; --card:#161b22; --border:#30363d; --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --green:#3fb950; }}
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
    pre {{ background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:0.75rem; overflow:auto; font-size:0.75rem; }}
    .ok {{ color:var(--green); }}
  </style>
</head>
<body>
  <header>
    <div><h1>Tape-to-Cloud Hub</h1><div class="muted">Discovery · inventory · forum-watcher · 16 modules</div></div>
    <nav class="nav">
      <a href="/monitor">Monitor</a>
      <a href="/monetize">Monetize</a>
      <a href="/tape-to-cloud">Tape-to-Cloud</a>
    </nav>
  </header>
  <main>
    <section>
      <h2>Status</h2>
      <p class="muted">Live JSON: <code>/api/tape-to-cloud/status</code></p>
      <p>Forum watcher seen URLs: <strong>{state['forum_watcher']['seen_url_count']}</strong></p>
      {latest_line}
      <p class="ok">Packages: tape_to_cloud.monetize={'yes' if state['packages']['tape_to_cloud_monetize'] else 'no'},
        forum-watcher={'yes' if state['packages']['forum_watcher'] else 'no'}</p>
    </section>
    <section>
      <h2>16 modules</h2>
      <ul class="modules">{modules_html}</ul>
    </section>
    <section>
      <h2>Discovery docs</h2>
      <table><thead><tr><th>Doc</th><th>Path</th><th>On disk</th></tr></thead><tbody>{docs_rows}</tbody></table>
    </section>
    <section>
      <h2>CLI quick start</h2>
      <pre>python3 ew_tool.py --monitor          # this Web UI (port 8765)
python3 ew_tool.py --monetize         # strategy report
python -m tape_to_cloud.monetize      # license / royalty CLI
cd forum-watcher && python scripts/watch.py</pre>
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
    query: Optional[Mapping[str, Sequence[str]]] = None,
) -> Optional[tuple[int, dict[str, str], bytes]]:
    path = path.rstrip("/") or "/"
    method = (method or "GET").upper()
    if method != "GET":
        return None
    if path in ("/tape-to-cloud", "/tape-to-cloud/"):
        body = render_hub_html().encode("utf-8")
        return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, body
    if path == "/api/tape-to-cloud/status":
        body = json.dumps(build_hub_state(), indent=2, default=str).encode("utf-8")
        return 200, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body
    return None


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
