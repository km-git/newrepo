"""
Monetize Explorer — local, offline-safe HTML + JSON for license tiers.

Reuses ``engine.monetize`` (AccessController, LicenseTagger, RoyaltyReporter).
Does not duplicate the feature matrix. Never runs live trading, scans, or daemons.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qs

from engine.monetize import (
    FEATURE_DESCRIPTIONS,
    TIERS,
    AccessController,
    LicenseTagger,
    RoyaltyReporter,
    env_tier_is_valid,
    env_tier_warning,
    features_for_tier,
    known_features,
    max_batch_size,
    monetize_status,
    raw_env_tier,
)

DEFAULT_OUTPUT_DIR = "output"
MONETIZE_HTML_PATH = "output/monetize.html"

# Same wording the CLI prints on exit 2 (ew_tool._LICENSE_UPGRADE_HINT).
LICENSE_UPGRADE_HINT = (
    "Upgrade via EW_LICENSE_TIER=pro or EW_LICENSE_TIER=enterprise. "
    "See --monetize-status."
)

#: Feature keys the explorer can try via AccessController.require() (no side effects).
DEMO_FEATURES: Tuple[str, ...] = (
    "single_symbol",
    "batch",
    "paper_execution",
    "brain_okf",
    "live_execution",
    "v6_scanner",
    "autonomous_daily",
)

Headers = Dict[str, str]
DispatchResult = Tuple[int, Headers, bytes]


def _min_tier_for(feature: str) -> Optional[str]:
    """Cheapest tier that includes *feature*, using the public matrix helpers."""
    for tier in TIERS:
        if feature in features_for_tier(tier):
            return tier
    return None


def _feature_rows(active_tier: Optional[str] = None) -> List[Dict[str, Any]]:
    ac = AccessController(tier=active_tier)
    rows: List[Dict[str, Any]] = []
    for key in sorted(
        known_features(),
        key=lambda k: (TIERS.index(_min_tier_for(k) or "enterprise"), k),
    ):
        min_tier = _min_tier_for(key)
        rows.append({
            "key": key,
            "description": FEATURE_DESCRIPTIONS.get(key, key),
            "min_tier": min_tier,
            "allowed": ac.can(key),
            "allowed_on": {t: key in features_for_tier(t) for t in TIERS},
        })
    return rows


def _tier_snapshot(tier: str) -> Dict[str, Any]:
    ac = AccessController(tier=tier)
    matrix = ac.access_matrix()
    return {
        "tier": ac.tier,
        "allowed": matrix["allowed"],
        "denied": matrix["denied"],
        "max_batch_size": max_batch_size(ac.tier),
    }


def build_explorer_state(tier: Optional[str] = None) -> Dict[str, Any]:
    """Serialisable explorer payload. *tier* previews without mutating the env."""
    process_ac = AccessController()
    ac = AccessController(tier=tier) if tier is not None else process_ac
    tagged = LicenseTagger.tag({}, tier=ac.tier)
    license_block = tagged["_license"]
    royalty = RoyaltyReporter.load()
    warning = env_tier_warning()
    raw = raw_env_tier()
    status = monetize_status(tier=ac.tier)
    state: Dict[str, Any] = {
        "license": {
            **ac.access_matrix(),
            "tagged_at": license_block["tagged_at"],
            "max_batch_size": max_batch_size(ac.tier),
        },
        "features": _feature_rows(ac.tier),
        "tiers": {t: _tier_snapshot(t) for t in TIERS},
        "royalty_report": royalty,
        "royalty_empty": not bool(royalty),
        "env_tier": raw,
        "env_tier_valid": env_tier_is_valid(raw),
        "process_tier": process_ac.tier,
        "preview": ac.tier != process_ac.tier,
        "demo_features": [
            {
                "key": key,
                "description": FEATURE_DESCRIPTIONS.get(key, key),
                "min_tier": _min_tier_for(key),
                "allowed": ac.can(key),
            }
            for key in DEMO_FEATURES
        ],
        "cli": {
            "status": "python3 ew_tool.py --monetize-status",
            "report": "python3 ew_tool.py --monetize-report",
            "ui": "python3 ew_tool.py --monetize-ui",
            "env": "EW_LICENSE_TIER=free|pro|enterprise",
        },
        "upgrade_hint": LICENSE_UPGRADE_HINT,
    }
    if warning:
        state["warning"] = warning
    # Keep monetize_status keys available for callers that expect them.
    state["status"] = status
    return state


def try_require(feature: str, tier: Optional[str] = None) -> Dict[str, Any]:
    """Call AccessController.require() only — never run the gated product action."""
    ac = AccessController(tier=tier)
    key = (feature or "").strip()
    try:
        ac.require(key)
        return {
            "ok": True,
            "feature": key,
            "tier": ac.tier,
            "exit_code": 0,
            "message": f"Feature '{key}' is allowed on the '{ac.tier}' tier.",
        }
    except AccessController.AccessDeniedError as exc:
        return {
            "ok": False,
            "feature": key,
            "tier": ac.tier,
            "exit_code": 2,
            "error": str(exc),
            "hint": LICENSE_UPGRADE_HINT,
        }


def set_demo_tier(tier: str) -> Dict[str, Any]:
    """Set EW_LICENSE_TIER for this local demo process only, then return state."""
    resolved = AccessController(tier=tier).tier
    os.environ["EW_LICENSE_TIER"] = resolved
    return build_explorer_state()


def write_monetize_html(output_dir: str = DEFAULT_OUTPUT_DIR) -> Path:
    path = Path(output_dir) / "monetize.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MONETIZE_HTML)
    return path


def publish_monetize(output_dir: str = DEFAULT_OUTPUT_DIR) -> Dict[str, str]:
    html_path = write_monetize_html(output_dir)
    return {"monetize_html": str(html_path)}


def _json_bytes(payload: Any, status: int = 200) -> DispatchResult:
    body = json.dumps(payload, indent=2, default=str).encode()
    return status, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
    }, body


def _parse_body(body: Optional[bytes], content_type: str = "") -> Dict[str, Any]:
    if not body:
        return {}
    raw = body.decode("utf-8", errors="replace")
    if "application/json" in (content_type or "") or raw.lstrip().startswith("{"):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {"_parse_error": "invalid JSON"}
    form = parse_qs(raw, keep_blank_values=True)
    return {k: v[0] if v else "" for k, v in form.items()}


def _q(query: Mapping[str, Sequence[str]], key: str, default: Optional[str] = None) -> Optional[str]:
    vals = query.get(key)
    if not vals:
        return default
    return vals[0]


def dispatch_monetize(
    method: str,
    path: str,
    query: Optional[Mapping[str, Sequence[str]]] = None,
    body: Optional[bytes] = None,
    *,
    content_type: str = "",
    root_is_monetize: bool = False,
) -> Optional[DispatchResult]:
    """Handle Monetize Explorer routes. Return None when the path is not ours."""
    query = query or {}
    method = (method or "GET").upper()
    path = path.rstrip("/") or "/"

    html_paths = {"/monetize"}
    if root_is_monetize:
        html_paths.add("/")
    if method == "GET" and path in html_paths:
        encoded = MONETIZE_HTML.encode("utf-8")
        return 200, {
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "no-store",
        }, encoded

    if path == "/api/monetize/status" and method == "GET":
        preview = _q(query, "tier")
        return _json_bytes(build_explorer_state(preview))

    if path == "/api/monetize/royalty" and method == "GET":
        royalty = RoyaltyReporter.load()
        return _json_bytes({
            "royalty_report": royalty,
            "royalty_empty": not bool(royalty),
        })

    if path == "/api/monetize/tier" and method in ("GET", "POST"):
        if method == "GET":
            preview = _q(query, "tier")
            return _json_bytes(build_explorer_state(preview))
        parsed = _parse_body(body, content_type)
        if parsed.get("_parse_error"):
            return _json_bytes({"error": "invalid JSON"}, 400)
        next_tier = parsed.get("tier") or _q(query, "tier")
        if not next_tier:
            return _json_bytes({"error": "missing tier"}, 400)
        return _json_bytes(set_demo_tier(str(next_tier)))

    if path == "/api/monetize/require" and method in ("GET", "POST"):
        parsed = _parse_body(body, content_type) if method == "POST" else {}
        if parsed.get("_parse_error"):
            return _json_bytes({"error": "invalid JSON"}, 400)
        feature = parsed.get("feature") or _q(query, "feature")
        preview = parsed.get("tier") or _q(query, "tier")
        if not feature:
            return _json_bytes({"error": "missing feature"}, 400)
        return _json_bytes(try_require(str(feature), str(preview) if preview else None))

    return None


def write_http_dispatch(
    handler: Any,
    result: DispatchResult,
) -> None:
    """Write a dispatch result onto a BaseHTTPRequestHandler."""
    status, headers, payload = result
    handler.send_response(status)
    for key, value in headers.items():
        handler.send_header(key, value)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def serve_monetize_http(
    handler: Any,
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]],
    body: bytes = b"",
    *,
    content_type: str = "",
    root_is_monetize: bool = False,
) -> bool:
    """Write a monetize response if this is our route. Return True when handled."""
    result = dispatch_monetize(
        method,
        path,
        query,
        body,
        content_type=content_type,
        root_is_monetize=root_is_monetize,
    )
    if result is None:
        return False
    write_http_dispatch(handler, result)
    return True


MONETIZE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Monetize Explorer</title>
  <style>
    :root {
      --bg: #0d1117;
      --panel: #161b22;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --green: #3fb950;
      --red: #f85149;
      --amber: #d29922;
      --blue: #58a6ff;
      --purple: #a371f7;
      --free: #8b949e;
      --pro: #58a6ff;
      --enterprise: #a371f7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }
    header {
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: center;
      justify-content: space-between;
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    h1 { margin: 0; font-size: 1.15rem; font-weight: 600; }
    .meta { color: var(--muted); font-size: 0.85rem; }
    .nav { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
    .nav a { color: var(--blue); text-decoration: none; font-size: 0.85rem; }
    .nav a:hover { text-decoration: underline; }
    main { padding: 1rem 1.25rem 2.5rem; max-width: 1180px; margin: 0 auto; }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.85rem 1rem;
    }
    .card .label { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }
    .card .value { font-size: 1.25rem; font-weight: 600; margin-top: 0.15rem; }
    section {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 1rem;
      overflow: hidden;
    }
    section h2 {
      margin: 0;
      padding: 0.75rem 1rem;
      font-size: 0.95rem;
      border-bottom: 1px solid var(--border);
      background: rgba(255,255,255,0.02);
    }
    .section-body { padding: 0.85rem 1rem; }
    .tier-switch { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    button {
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.4rem 0.75rem;
      font-size: 0.85rem;
      cursor: pointer;
    }
    button:hover { border-color: var(--blue); }
    button.active-free { border-color: var(--free); box-shadow: 0 0 0 1px var(--free); }
    button.active-pro { border-color: var(--pro); box-shadow: 0 0 0 1px var(--pro); }
    button.active-enterprise { border-color: var(--enterprise); box-shadow: 0 0 0 1px var(--enterprise); }
    .pill {
      display: inline-block;
      padding: 0.12rem 0.5rem;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .pill.free { background: rgba(139,148,158,0.18); color: var(--free); }
    .pill.pro { background: rgba(88,166,255,0.16); color: var(--pro); }
    .pill.enterprise { background: rgba(163,113,247,0.18); color: var(--enterprise); }
    .pill.ok { background: rgba(63,185,80,0.15); color: var(--green); }
    .pill.no { background: rgba(248,81,73,0.15); color: var(--red); }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th, td { padding: 0.45rem 0.5rem; text-align: left; border-bottom: 1px solid var(--border); vertical-align: top; }
    th { color: var(--muted); font-weight: 500; }
    tr.denied td { opacity: 0.72; }
    tr.highlight td { background: rgba(88,166,255,0.06); }
    .check { color: var(--green); font-weight: 700; }
    .cross { color: var(--red); font-weight: 700; }
    .empty {
      color: var(--muted);
      padding: 0.75rem 0;
      font-size: 0.9rem;
    }
    .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    .banner {
      margin-top: 0.85rem;
      padding: 0.75rem 0.85rem;
      border-radius: 6px;
      border: 1px solid var(--border);
      font-size: 0.88rem;
      white-space: pre-wrap;
    }
    .banner.ok { border-color: rgba(63,185,80,0.4); background: rgba(63,185,80,0.08); }
    .banner.deny { border-color: rgba(248,81,73,0.4); background: rgba(248,81,73,0.08); }
    code, pre {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.8rem;
    }
    pre {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.75rem 0.85rem;
      overflow: auto;
    }
    .warn { color: var(--amber); font-size: 0.85rem; margin-bottom: 0.75rem; }
    .preview-note { color: var(--amber); }
    #status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); display: inline-block; }
    #status-dot.live { background: var(--green); }
    .error { color: var(--red); padding: 0.5rem 0; }
    ul.detail { margin: 0.4rem 0 0; padding-left: 1.1rem; color: var(--muted); font-size: 0.82rem; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Monetize Explorer</h1>
      <div class="meta" id="meta">Loading license status…</div>
    </div>
    <div class="nav">
      <span id="status-dot"></span>
      <a href="/monitor">Monitor</a>
      <a href="/monetize">Monetize</a>
      <button id="btn-refresh" type="button">Refresh</button>
    </div>
  </header>
  <main>
    <div id="error" class="error" hidden></div>
    <div id="warning" class="warn" hidden></div>
    <div class="cards" id="cards"></div>

    <section>
      <h2>Interactive tier switcher</h2>
      <div class="section-body">
        <p class="meta">Preview re-renders the access matrix for a tier. Apply writes <code>EW_LICENSE_TIER</code> on this local demo process only.</p>
        <div class="tier-switch" id="tier-switch"></div>
        <p class="meta" id="tier-note" style="margin-top:0.75rem"></p>
      </div>
    </section>

    <section>
      <h2>Access matrix</h2>
      <div class="section-body" style="overflow:auto">
        <table id="matrix">
          <thead>
            <tr>
              <th>Feature</th>
              <th>Description</th>
              <th>Free</th>
              <th>Pro</th>
              <th>Enterprise</th>
              <th>This tier</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Royalty report</h2>
      <div class="section-body" id="royalty"></div>
    </section>

    <section>
      <h2>Try a gated action</h2>
      <div class="section-body">
        <p class="meta">Calls <code>AccessController.require()</code> only. Does not run live trading, v6 scans, or autonomous daily.</p>
        <div class="actions" id="demo-actions"></div>
        <div id="require-result" hidden></div>
      </div>
    </section>

    <section>
      <h2>How to use the CLI</h2>
      <div class="section-body">
        <pre id="cli-help">python3 ew_tool.py --monetize-status
python3 ew_tool.py --monetize-report
python3 ew_tool.py --monetize-ui
EW_LICENSE_TIER=free|pro|enterprise</pre>
      </div>
    </section>
  </main>
  <script>
    const STATUS_API = "/api/monetize/status";
    const TIER_API = "/api/monetize/tier";
    const REQUIRE_API = "/api/monetize/require";
    let state = null;

    function qsTier() {
      return new URLSearchParams(location.search).get("tier");
    }

    function mark(ok) {
      return ok ? '<span class="check">✓</span>' : '<span class="cross">✗</span>';
    }

    function pill(tier) {
      const t = (tier || "").toLowerCase();
      return '<span class="pill ' + t + '">' + (tier || "—") + '</span>';
    }

    function renderCards(d) {
      const lic = d.license || {};
      const royalty = d.royalty_report || {};
      const usage = royalty.usage || {};
      const batch = lic.max_batch_size == null ? "unlimited" : lic.max_batch_size;
      document.getElementById("cards").innerHTML = [
        ["License tier", pill(lic.tier)],
        ["Tagged at", lic.tagged_at || "—"],
        ["Allowed features", (lic.allowed || []).length],
        ["Denied features", (lic.denied || []).length],
        ["Batch cap", batch],
        ["Setups recorded", d.royalty_empty ? "—" : (usage.setups_generated ?? 0)],
      ].map(([label, value]) =>
        '<div class="card"><div class="label">' + label + '</div><div class="value">' + value + '</div></div>'
      ).join("");
    }

    function renderSwitcher(d) {
      const active = (d.license || {}).tier;
      const processTier = d.process_tier;
      document.getElementById("tier-switch").innerHTML = ["free", "pro", "enterprise"].map((tier) => {
        const cls = tier === active ? " active-" + tier : "";
        return '<button type="button" class="tier-btn' + cls + '" data-tier="' + tier + '">' +
          tier.charAt(0).toUpperCase() + tier.slice(1) + '</button>';
      }).join("") +
        '<button type="button" id="btn-apply">Apply to demo process</button>';
      document.querySelectorAll(".tier-btn").forEach((btn) => {
        btn.addEventListener("click", () => previewTier(btn.getAttribute("data-tier")));
      });
      document.getElementById("btn-apply").addEventListener("click", () => applyTier(active));
      const note = document.getElementById("tier-note");
      if (d.preview) {
        note.innerHTML = '<span class="preview-note">Previewing ' + pill(active) +
          ' — demo process is still ' + pill(processTier) + '.</span>';
      } else {
        note.textContent = "Showing the demo process tier (" + processTier + ").";
      }
    }

    function renderMatrix(d) {
      const tbody = document.querySelector("#matrix tbody");
      const active = (d.license || {}).tier;
      tbody.innerHTML = (d.features || []).map((row) => {
        const on = row.allowed_on || {};
        const cls = row.allowed ? "highlight" : "denied";
        return '<tr class="' + cls + '"><td><code>' + row.key + '</code></td><td>' +
          (row.description || "") + '</td><td>' + mark(on.free) + '</td><td>' +
          mark(on.pro) + '</td><td>' + mark(on.enterprise) + '</td><td>' +
          (row.allowed ? '<span class="pill ok">allowed</span>' : '<span class="pill no">denied</span>') +
          '</td></tr>';
      }).join("");
      void active;
    }

    function renderRoyalty(d) {
      const el = document.getElementById("royalty");
      if (d.royalty_empty) {
        el.innerHTML = '<div class="empty">No royalty report yet. Run <code>python3 ew_tool.py --monetize-report</code> or complete an analysis to create <code>output/system/royalty_report.json</code>.</div>';
        return;
      }
      const r = d.royalty_report || {};
      const usage = r.usage || {};
      const detail = r.detail || {};
      const setups = detail.setups || [];
      const signals = detail.signals || [];
      const tickers = detail.tickers || [];
      el.innerHTML =
        '<div class="cards">' +
          '<div class="card"><div class="label">Setups</div><div class="value">' + (usage.setups_generated ?? 0) + '</div></div>' +
          '<div class="card"><div class="label">Signals</div><div class="value">' + (usage.signals_fired ?? 0) + '</div></div>' +
          '<div class="card"><div class="label">Tickers</div><div class="value">' + (usage.tickers_scanned ?? 0) + '</div></div>' +
        '</div>' +
        '<div class="meta">Generated ' + (r.generated_at || "—") + ' · report tier ' + pill(r.tier) + '</div>' +
        '<ul class="detail">' +
          '<li>Setups: ' + (setups.length ? setups.slice(0, 12).join(", ") : "none") + (setups.length > 12 ? "…" : "") + '</li>' +
          '<li>Signals: ' + (signals.length ? signals.slice(0, 8).map(s => (s.symbol || s) + (s.direction ? " " + s.direction : "")).join(", ") : "none") + '</li>' +
          '<li>Tickers: ' + (tickers.length ? tickers.slice(0, 12).join(", ") : "none") + '</li>' +
        '</ul>';
    }

    function renderActions(d) {
      const box = document.getElementById("demo-actions");
      box.innerHTML = (d.demo_features || []).map((f) => {
        const label = f.key.replace(/_/g, " ");
        return '<button type="button" data-feature="' + f.key + '">' + label + '</button>';
      }).join("");
      box.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => tryFeature(btn.getAttribute("data-feature")));
      });
    }

    function renderCli(d) {
      const c = d.cli || {};
      document.getElementById("cli-help").textContent =
        (c.status || "python3 ew_tool.py --monetize-status") + "\\n" +
        (c.report || "python3 ew_tool.py --monetize-report") + "\\n" +
        (c.ui || "python3 ew_tool.py --monetize-ui") + "\\n" +
        (c.env || "EW_LICENSE_TIER=free|pro|enterprise");
    }

    function render(d) {
      state = d;
      const lic = d.license || {};
      document.getElementById("meta").innerHTML =
        "Tier " + pill(lic.tier) +
        (d.preview ? ' <span class="preview-note">(preview)</span>' : "") +
        " · tagged " + (lic.tagged_at || "—") +
        " · env " + (d.env_tier || "free");
      document.getElementById("status-dot").classList.add("live");
      const warn = document.getElementById("warning");
      if (d.warning) {
        warn.hidden = false;
        warn.textContent = d.warning;
      } else {
        warn.hidden = true;
      }
      renderCards(d);
      renderSwitcher(d);
      renderMatrix(d);
      renderRoyalty(d);
      renderActions(d);
      renderCli(d);
    }

    async function load(tier) {
      const err = document.getElementById("error");
      err.hidden = true;
      const q = new URLSearchParams();
      if (tier) q.set("tier", tier);
      q.set("t", String(Date.now()));
      try {
        const res = await fetch(STATUS_API + "?" + q.toString());
        if (!res.ok) throw new Error("HTTP " + res.status);
        render(await res.json());
      } catch (e) {
        err.hidden = false;
        err.textContent = "Failed to load Monetize Explorer: " + e.message +
          ". Start with: python3 ew_tool.py --monetize-ui";
        document.getElementById("status-dot").classList.remove("live");
      }
    }

    async function previewTier(tier) {
      const url = new URL(location.href);
      url.searchParams.set("tier", tier);
      history.replaceState(null, "", url);
      await load(tier);
    }

    async function applyTier(tier) {
      const res = await fetch(TIER_API, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({tier: tier})
      });
      const d = await res.json();
      const url = new URL(location.href);
      url.searchParams.set("tier", (d.license || {}).tier || tier);
      history.replaceState(null, "", url);
      render(d);
    }

    async function tryFeature(feature) {
      const tier = qsTier() || (state && state.license && state.license.tier);
      const q = new URLSearchParams({feature: feature});
      if (tier) q.set("tier", tier);
      const res = await fetch(REQUIRE_API + "?" + q.toString());
      const d = await res.json();
      const el = document.getElementById("require-result");
      el.hidden = false;
      el.className = "banner " + (d.ok ? "ok" : "deny");
      if (d.ok) {
        el.textContent = d.message + "\\nAccessController.require('" + feature + "') passed.";
      } else {
        el.textContent = (d.error || "Denied") + "\\n" +
          (d.hint || "") + "\\nCLI would exit " + (d.exit_code ?? 2) + ".";
      }
    }

    document.getElementById("btn-refresh").addEventListener("click", () => load(qsTier()));
    load(qsTier());
  </script>
</body>
</html>
"""

