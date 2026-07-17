"""Browser monitor — aggregate output/ artifacts into dashboard_state.json + monitor.html."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_OUTPUT_DIR = "output"
DASHBOARD_STATE_PATH = "output/autodream/dashboard_state.json"
MONITOR_HTML_PATH = "output/monitor.html"


def _utcnow_iso() -> str:
  return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Optional[dict]:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text())
  except (json.JSONDecodeError, OSError):
    return None


def _latest_glob(out: Path, pattern: str) -> Optional[Path]:
  files = sorted(out.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
  return files[0] if files else None


def _read_summary_csv(path: Path) -> List[dict]:
  if not path.exists():
    return []
  with path.open(newline="") as f:
    return list(csv.DictReader(f))


def _tail_jsonl(path: Path, limit: int = 30) -> List[dict]:
  if not path.exists():
    return []
  lines: List[str] = []
  with path.open() as f:
    for line in f:
      line = line.strip()
      if line:
        lines.append(line)
  rows = []
  for line in lines[-limit:]:
    try:
      rows.append(json.loads(line))
    except json.JSONDecodeError:
      continue
  return rows


def discover_paths(output_dir: str = DEFAULT_OUTPUT_DIR) -> dict:
  """Resolve stable + latest artifact paths."""
  out = Path(output_dir)
  paths_doc = _read_json(out / "autodream" / "latest_paths.json") or {}
  meta_glob = _latest_glob(out, "top*_meta_*.json")
  meta = _read_json(meta_glob) if meta_glob else {}

  summary = out / "latest_summary.csv"
  if not summary.exists():
    latest = _latest_glob(out, "top*_summary_*.csv")
    summary = latest or summary

  return {
    "dashboard_state": str(out / "autodream" / "dashboard_state.json"),
    "monitor_html": str(out / "monitor.html"),
    "monitor_queue": str(out / "autodream" / "monitor_queue.json"),
    "metrics": str(out / "autodream" / "metrics.json"),
    "scheduler_state": str(out / "autodream" / "scheduler_state.json"),
    "limit_orders_meta": str(out / "autodream" / "latest_limit_orders.json"),
    "matrix_html": str(out / "latest_trade_setups_matrix.html"),
    "setups_html": str(out / "latest_setups.html"),
    "summary_csv": str(summary) if summary.exists() else meta.get("summary_csv"),
    "analysis_json": paths_doc.get("json") or meta.get("json"),
    "batch_timestamp": paths_doc.get("batch_timestamp") or meta.get("timestamp_utc"),
    "pairs_count": paths_doc.get("pairs_count") or meta.get("pairs_count"),
    "by_verdict": paths_doc.get("by_verdict") or meta.get("by_verdict"),
    "by_status": paths_doc.get("by_status") or meta.get("by_status"),
    "updated": paths_doc.get("updated"),
  }


def build_dashboard_state(output_dir: str = DEFAULT_OUTPUT_DIR) -> dict:
  """Slim JSON snapshot for the browser monitor."""
  out = Path(output_dir)
  paths = discover_paths(output_dir)

  monitor_doc = _read_json(Path(paths["monitor_queue"])) or {}
  metrics = _read_json(Path(paths["metrics"])) or {}
  limit_meta = _read_json(Path(paths["limit_orders_meta"])) or {}
  scheduler = _read_json(Path(paths["scheduler_state"])) or {}

  queue = monitor_doc.get("queue") or []
  status_counts = Counter(item.get("status") for item in queue)
  style_counts = Counter(item.get("style") for item in queue)

  summary_rows = _read_summary_csv(Path(paths["summary_csv"])) if paths.get("summary_csv") else []
  verdict_counts = Counter(r.get("verdict") for r in summary_rows if r.get("verdict"))
  pipeline_counts = Counter(r.get("status") for r in summary_rows if r.get("status"))

  executable = [q for q in queue if q.get("status") == "executable"]
  monitor_only = [q for q in queue if q.get("status") == "monitor"]

  events = _tail_jsonl(out / "autodream" / "monitor_events.jsonl", limit=25)

  overall = metrics.get("overall") or {}
  by_direction = metrics.get("by_direction") or {}

  return {
    "updated": _utcnow_iso(),
    "batch_timestamp": paths.get("batch_timestamp"),
    "pairs_count": paths.get("pairs_count") or len(summary_rows),
    "by_verdict": dict(verdict_counts) or paths.get("by_verdict") or {},
    "by_status": dict(pipeline_counts) or paths.get("by_status") or {},
    "queue": {
      "updated": monitor_doc.get("updated"),
      "total": len(queue),
      "executable": len(executable),
      "monitor": len(monitor_only),
      "by_style": dict(style_counts),
      "by_status": dict(status_counts),
    },
    "metrics": {
      "updated": metrics.get("updated"),
      "win_rate": overall.get("win_rate"),
      "wins": overall.get("wins"),
      "losses": overall.get("losses"),
      "decided": overall.get("decided"),
      "open_count": metrics.get("open_count"),
      "closed_count": metrics.get("closed_count"),
      "by_direction": {
        k: {"win_rate": v.get("win_rate"), "decided": v.get("decided")}
        for k, v in by_direction.items()
      },
      "by_timeframe": {
        k: {"win_rate": v.get("win_rate"), "decided": v.get("decided")}
        for k, v in (metrics.get("by_timeframe") or {}).items()
      },
    },
    "limit_orders": {
      "tier_counts": limit_meta.get("tier_counts") or limit_meta.get("by_gtc_tier"),
      "row_count": limit_meta.get("row_count"),
      "pairs": limit_meta.get("pairs"),
    },
    "scheduler": {
      "last_batch_utc": scheduler.get("last_batch_utc"),
      "last_monitor_utc": scheduler.get("last_monitor_utc"),
    },
    "summary": summary_rows,
    "executable_queue": sorted(
      executable,
      key=lambda x: (x.get("symbol", ""), x.get("style", "")),
    )[:64],
    "monitor_queue_sample": sorted(
      monitor_only,
      key=lambda x: (x.get("symbol", ""), x.get("style", "")),
    )[:48],
    "recent_events": events,
    "paths": paths,
  }


def write_dashboard_state(output_dir: str = DEFAULT_OUTPUT_DIR) -> Path:
  state = build_dashboard_state(output_dir)
  path = Path(output_dir) / "autodream" / "dashboard_state.json"
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(state, indent=2, default=str))
  return path


MONITOR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>EW Monitor</title>
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
    .controls { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
    button, select, input {
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.35rem 0.65rem;
      font-size: 0.85rem;
    }
    button { cursor: pointer; }
    button:hover { border-color: var(--blue); }
    main { padding: 1rem 1.25rem 2rem; max-width: 1600px; margin: 0 auto; }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
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
    .card .value { font-size: 1.35rem; font-weight: 600; margin-top: 0.15rem; }
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    @media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
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
    .section-body { padding: 0.75rem 1rem; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th, td { padding: 0.45rem 0.5rem; text-align: left; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-weight: 500; position: sticky; top: 0; background: var(--panel); }
    tr:hover td { background: rgba(88,166,255,0.06); }
    .scroll { max-height: 420px; overflow: auto; }
    .pill {
      display: inline-block;
      padding: 0.1rem 0.45rem;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 600;
    }
    .go { background: rgba(63,185,80,0.15); color: var(--green); }
    .cond { background: rgba(210,153,34,0.15); color: var(--amber); }
    .standby { background: rgba(88,166,255,0.12); color: var(--blue); }
    .staged { background: rgba(163,113,247,0.15); color: var(--purple); }
    .exec { background: rgba(63,185,80,0.2); color: var(--green); }
    .mon { background: rgba(210,153,34,0.12); color: var(--amber); }
    .long { color: var(--green); }
    .short { color: var(--red); }
    .bar-row { display: flex; align-items: center; gap: 0.5rem; margin: 0.35rem 0; font-size: 0.82rem; }
    .bar { flex: 1; height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden; }
    .bar > span { display: block; height: 100%; background: var(--blue); }
    iframe {
      width: 100%;
      height: 520px;
      border: 0;
      background: #fff;
    }
    .error { color: var(--red); padding: 1rem; }
    .links { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    .links a { color: var(--blue); text-decoration: none; font-size: 0.85rem; }
    .links a:hover { text-decoration: underline; }
    #status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); display: inline-block; }
    #status-dot.live { background: var(--green); }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>EW + Harmonic Monitor</h1>
      <div class="meta" id="meta">Loading…</div>
    </div>
    <div class="controls">
      <span id="status-dot"></span>
      <select id="refresh-interval">
        <option value="0">Manual</option>
        <option value="15">15s</option>
        <option value="30" selected>30s</option>
        <option value="60">60s</option>
      </select>
      <button id="btn-refresh">Refresh</button>
    </div>
  </header>
  <main>
    <div id="error" class="error" hidden></div>
    <div class="cards" id="cards"></div>
    <div class="grid-2">
      <section>
        <h2>Executive verdicts</h2>
        <div class="section-body" id="verdicts"></div>
      </section>
      <section>
        <h2>Performance</h2>
        <div class="section-body" id="performance"></div>
      </section>
    </div>
    <section>
      <h2>Pair summary <input id="filter-symbol" placeholder="Filter symbol…" style="float:right;margin-top:-2px"/></h2>
      <div class="section-body scroll">
        <table id="summary-table">
          <thead><tr>
            <th>Symbol</th><th>Status</th><th>Verdict</th><th>Dir</th><th>Conf</th><th>Consensus</th><th>Action</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>
    <section>
      <h2>Executable queue</h2>
      <div class="section-body scroll">
        <table id="exec-table">
          <thead><tr>
            <th>Symbol</th><th>Style</th><th>Dir</th><th>Entry</th><th>Stop</th><th>TP1</th><th>Check</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>
    <section>
      <h2>Trade matrix</h2>
      <div class="section-body">
        <div class="links" id="links"></div>
        <iframe id="matrix-frame" title="Trade setups matrix"></iframe>
      </div>
    </section>
  </main>
  <script>
    const API = "/api/dashboard";
    let timer = null;

    function pillVerdict(v) {
      if (!v) return "";
      if (v === "GO") return '<span class="pill go">GO</span>';
      if (v.includes("CONDITIONAL")) return '<span class="pill cond">'+v+'</span>';
      if (v.includes("STANDBY")) return '<span class="pill standby">'+v+'</span>';
      if (v.includes("STAGED")) return '<span class="pill staged">'+v+'</span>';
      return '<span class="pill">'+v+'</span>';
    }

    function fmtPct(x) {
      if (x == null) return "—";
      return (x * 100).toFixed(1) + "%";
    }

    function fmtNum(x) {
      if (x == null || x === "") return "—";
      const n = Number(x);
      if (Number.isNaN(n)) return x;
      if (Math.abs(n) >= 1000) return n.toLocaleString(undefined, {maximumFractionDigits: 2});
      if (Math.abs(n) >= 1) return n.toFixed(4);
      return n.toPrecision(4);
    }

    function barRow(label, count, total, color) {
      const pct = total ? (count / total * 100) : 0;
      return `<div class="bar-row"><span style="width:7rem">${label}</span><div class="bar"><span style="width:${pct}%;background:${color||'var(--blue)'}"></span></div><span>${count}</span></div>`;
    }

    function renderCards(d) {
      const m = d.metrics || {};
      const q = d.queue || {};
      const lo = d.limit_orders || {};
      const tiers = lo.tier_counts || {};
      document.getElementById("cards").innerHTML = [
        ["Pairs", d.pairs_count || "—"],
        ["Executable", q.executable || 0],
        ["Monitor queue", q.monitor || 0],
        ["Win rate", fmtPct(m.win_rate)],
        ["W / L", (m.wins ?? "—") + " / " + (m.losses ?? "—")],
        ["Matrix exec", tiers.executable || "—"],
      ].map(([label, value]) => `<div class="card"><div class="label">${label}</div><div class="value">${value}</div></div>`).join("");
    }

    function renderVerdicts(d) {
      const v = d.by_verdict || {};
      const total = Object.values(v).reduce((a,b)=>a+b,0) || 1;
      const colors = { GO: "var(--green)", CONDITIONAL_GO: "var(--amber)", STANDBY_ORDERS: "var(--blue)", STAGED_GO: "var(--purple)" };
      document.getElementById("verdicts").innerHTML = Object.entries(v)
        .sort((a,b)=>b[1]-a[1])
        .map(([k,c]) => barRow(k, c, total, colors[k]))
        .join("") || "<span class='meta'>No summary data — run a batch first.</span>";
    }

    function renderPerformance(d) {
      const m = d.metrics || {};
      let html = `<div><strong>Overall</strong> ${fmtPct(m.win_rate)} (${m.decided || 0} decided)</div>`;
      const bd = m.by_direction || {};
      html += Object.entries(bd).map(([dir, stats]) =>
        `<div class="bar-row"><span class="${dir==='LONG'?'long':'short'}" style="width:4rem">${dir}</span> ${fmtPct(stats.win_rate)} <span class="meta">(${stats.decided})</span></div>`
      ).join("");
      const tf = m.by_timeframe || {};
      if (Object.keys(tf).length) {
        html += "<div style='margin-top:0.5rem'><strong>By TF</strong></div>";
        html += Object.entries(tf).map(([tf, stats]) =>
          `<div class="meta">${tf}: ${fmtPct(stats.win_rate)} (${stats.decided})</div>`
        ).join("");
      }
      document.getElementById("performance").innerHTML = html;
    }

    function renderSummary(d, filter) {
      const rows = (d.summary || []).filter(r => !filter || (r.symbol||"").toLowerCase().includes(filter.toLowerCase()));
      const tbody = document.querySelector("#summary-table tbody");
      tbody.innerHTML = rows.map(r => `<tr>
        <td><strong>${r.symbol||""}</strong></td>
        <td>${r.status||""}</td>
        <td>${pillVerdict(r.verdict)}</td>
        <td class="${(r.direction||'').toLowerCase()}">${r.direction||""}</td>
        <td>${r.confidence||""}</td>
        <td>${r.consensus_direction||""} ${r.agreement_pct ? '('+r.agreement_pct+'%)' : ''}</td>
        <td class="meta">${r.action||""}</td>
      </tr>`).join("");
    }

    function renderExec(d) {
      const rows = d.executable_queue || [];
      const tbody = document.querySelector("#exec-table tbody");
      tbody.innerHTML = rows.length ? rows.map(r => `<tr>
        <td><strong>${r.symbol||""}</strong></td>
        <td>${r.style||""}</td>
        <td class="${(r.direction||'').toLowerCase()}">${r.direction||""}</td>
        <td>${fmtNum(r.entry)}</td>
        <td>${fmtNum(r.stop)}</td>
        <td>${fmtNum(r.tp1)}</td>
        <td>${r.check||""}</td>
      </tr>`).join("") : `<tr><td colspan="7" class="meta">No executable setups in queue.</td></tr>`;
    }

    function renderLinks(d) {
      const p = d.paths || {};
      const links = [
        ["Matrix HTML", p.matrix_html],
        ["Setups HTML", p.setups_html],
        ["Summary CSV", p.summary_csv],
        ["Full JSON", p.analysis_json],
      ].filter(([,u]) => u);
      document.getElementById("links").innerHTML = links.map(([t,u]) => `<a href="/${u.replace(/^\\//,'')}" target="_blank">${t}</a>`).join("");
      if (p.matrix_html) {
        document.getElementById("matrix-frame").src = "/" + p.matrix_html.replace(/^\\//,'');
      }
    }

    async function load() {
      const err = document.getElementById("error");
      err.hidden = true;
      try {
        const res = await fetch(API + "?t=" + Date.now());
        if (!res.ok) throw new Error("HTTP " + res.status);
        const d = await res.json();
        document.getElementById("meta").textContent =
          `Batch: ${d.batch_timestamp || "n/a"} · Updated: ${d.updated || "n/a"}`;
        document.getElementById("status-dot").classList.add("live");
        renderCards(d);
        renderVerdicts(d);
        renderPerformance(d);
        renderSummary(d, document.getElementById("filter-symbol").value);
        renderExec(d);
        renderLinks(d);
      } catch (e) {
        err.textContent = "Failed to load dashboard: " + e.message + ". Start server: python3 scripts/serve_monitor.py";
        err.hidden = false;
        document.getElementById("status-dot").classList.remove("live");
      }
    }

    function setupRefresh() {
      if (timer) clearInterval(timer);
      const sec = Number(document.getElementById("refresh-interval").value);
      if (sec > 0) timer = setInterval(load, sec * 1000);
    }

    document.getElementById("btn-refresh").addEventListener("click", load);
    document.getElementById("refresh-interval").addEventListener("change", setupRefresh);
    document.getElementById("filter-symbol").addEventListener("input", () => load());
    load();
    setupRefresh();
  </script>
</body>
</html>
"""


def write_monitor_html(output_dir: str = DEFAULT_OUTPUT_DIR) -> Path:
  path = Path(output_dir) / "monitor.html"
  path.write_text(MONITOR_HTML)
  return path


def publish_monitor(output_dir: str = DEFAULT_OUTPUT_DIR) -> dict:
  """Write dashboard_state.json + monitor.html."""
  state_path = write_dashboard_state(output_dir)
  html_path = write_monitor_html(output_dir)
  return {"dashboard_state": str(state_path), "monitor_html": str(html_path)}
