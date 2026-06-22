"""Unified full analysis table — all confluences + all trade setups per pair."""

from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from engine.outcome_report import build_outcome_row
from engine.report import build_detailed_row, _fmt_harmonics


STYLES = ("scalp", "day_trade", "swing", "long_term")


def _style_columns(setup: dict, prefix: str) -> dict:
  """Flatten one style setup into prefixed columns."""
  if not setup:
    return {f"{prefix}_status": "", f"{prefix}_direction": ""}

  targets = setup.get("targets") or []
  dca = setup.get("dca") or []
  harm = setup.get("harmonic")

  return {
    f"{prefix}_status": setup.get("status"),
    f"{prefix}_direction": setup.get("direction"),
    f"{prefix}_tf": setup.get("timeframe"),
    f"{prefix}_horizon": setup.get("horizon"),
    f"{prefix}_reason": setup.get("honest_reason"),
    f"{prefix}_wave": setup.get("wave_structure"),
    f"{prefix}_wave_valid": "Y" if setup.get("wave_valid") else "N",
    f"{prefix}_entry": setup.get("entry", {}).get("anchor"),
    f"{prefix}_zone_low": (setup.get("entry", {}).get("zone") or [None])[0],
    f"{prefix}_zone_high": (setup.get("entry", {}).get("zone") or [None, None])[1],
    f"{prefix}_dca_10": dca[0]["price"] if len(dca) > 0 else "",
    f"{prefix}_dca_20": dca[1]["price"] if len(dca) > 1 else "",
    f"{prefix}_dca_30": dca[2]["price"] if len(dca) > 2 else "",
    f"{prefix}_dca_40": dca[3]["price"] if len(dca) > 3 else "",
    f"{prefix}_stop": setup.get("stop_loss", {}).get("price"),
    f"{prefix}_tp1": targets[0]["price"] if len(targets) > 0 else "",
    f"{prefix}_tp2": targets[1]["price"] if len(targets) > 1 else "",
    f"{prefix}_tp3": targets[2]["price"] if len(targets) > 2 else "",
    f"{prefix}_rr": targets[1]["rr"] if len(targets) > 1 else "",
    f"{prefix}_risk_pct": setup.get("risk", {}).get("account_risk_pct"),
    f"{prefix}_harmonic": (
      f"{harm['pattern']}@{harm['prz_low']:.4g}" if harm else ""
    ),
  }


def build_full_row(result: dict) -> dict:
  """One wide row per symbol: confluences + executive + all 4 style setups."""
  base = build_detailed_row(result)
  if base.get("status") == "incomplete":
    return base

  ex = result.get("executive_decision", {})
  cons = result.get("step6_wave_consensus", {})
  oc = result.get("step8_outcomes", {})
  hs = oc.get("honest_summary", {})
  gaps = ex.get("structural_gaps", [])

  base.update({
    "executive_playbook": ex.get("playbook"),
    "executive_conviction": ex.get("conviction"),
    "executive_size_pct": ex.get("position_size_pct"),
    "structural_gaps": "; ".join(gaps[:3]) if gaps else "",
    "consensus_score": cons.get("consensus_score"),
    "engines_valid": cons.get("engines_valid"),
    "engine_divergences": "; ".join(cons.get("divergences", [])[:2]),
    "outcome_truth": hs.get("truth", ""),
    "primary_style": hs.get("primary_style", ""),
    "primary_outcome_status": hs.get("primary_status", ""),
    "executable_count": hs.get("executable_count", ""),
    "monitor_count": hs.get("monitor_count", ""),
    "not_actionable_count": hs.get("not_actionable_count", ""),
  })

  setups = oc.get("setups", {})
  for style in STYLES:
    base.update(_style_columns(setups.get(style, {}), style))

  return base


def build_setup_rows(result: dict) -> List[dict]:
  """One row per symbol × style with key confluences attached (filter-friendly)."""
  if result.get("status") == "incomplete":
    return [{"symbol": result.get("symbol"), "style": "—", "status": "error", "error": result.get("error")}]

  detail = build_detailed_row(result)
  confluence = {
    k: detail.get(k)
    for k in (
      "price", "htf_state", "htf_bias", "kill_zone_low", "kill_zone_high",
      "in_kill_zone", "harmonics_all", "harmonics_in_zone", "verdict", "action",
      "consensus", "agreement_pct", "15m_valid",
      "1d_structure", "4h_structure", "1h_structure", "15m_structure",
    )
  }

  rows = []
  for style_row in build_outcome_row(result):
    rows.append({**confluence, **style_row})
  return rows


def _collect_keys(rows: List[dict]) -> List[str]:
  keys: list[str] = []
  seen = set()
  for row in rows:
    for k in row:
      if k not in seen:
        seen.add(k)
        keys.append(k)
  return keys


def save_full_csv(results: List[dict], path: str) -> None:
  rows = [build_full_row(r) for r in results]
  rows = [r for r in rows if r]
  if not rows:
    return
  with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=_collect_keys(rows), extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)


def save_setups_csv(results: List[dict], path: str) -> None:
  rows: List[dict] = []
  for r in results:
    rows.extend(build_setup_rows(r))
  if not rows:
    return
  with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=_collect_keys(rows), extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)


def save_full_html(results: List[dict], path: str, title: str = "Full Analysis") -> None:
  """Scrollable HTML table — all pairs, confluences, and setups."""
  rows = [build_full_row(r) for r in results if r.get("status") != "incomplete"]
  if not rows:
    Path(path).write_text(f"<html><body><h1>{html.escape(title)}</h1><p>No data</p></body></html>")
    return

  # Priority columns first, then rest
  priority = [
    "symbol", "price", "verdict", "action", "direction", "outcome_truth",
    "primary_style", "primary_outcome_status", "executable_count", "monitor_count",
    "htf_state", "htf_bias", "kill_zone_low", "kill_zone_high", "in_kill_zone",
    "harmonics_in_zone", "harmonics_all", "consensus", "agreement_pct", "15m_valid",
    "1w_structure", "1d_structure", "4h_structure", "1h_structure", "15m_structure",
    "stop_loss", "take_profit_1", "risk_reward", "confidence",
  ]
  for style in STYLES:
    priority.extend([
      f"{style}_status", f"{style}_direction", f"{style}_entry",
      f"{style}_stop", f"{style}_tp1", f"{style}_tp2", f"{style}_rr", f"{style}_reason",
    ])

  all_keys = _collect_keys(rows)
  cols = [c for c in priority if c in all_keys] + [c for c in all_keys if c not in priority]

  def cell(v: Any) -> str:
    if v is None:
      return ""
    s = str(v)
    return html.escape(s[:120] + ("…" if len(s) > 120 else ""))

  thead = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
  body_rows = []
  for row in rows:
    cells = "".join(f"<td>{cell(row.get(c))}</td>" for c in cols)
    status_cls = ""
    ps = row.get("primary_outcome_status", "")
    if ps == "executable":
      status_cls = ' class="exec"'
    elif ps == "monitor":
      status_cls = ' class="mon"'
    body_rows.append(f"<tr{status_cls}>{cells}</tr>")

  doc = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
  h1 {{ font-size: 1.25rem; }}
  .wrap {{ overflow-x: auto; max-width: 100%; border: 1px solid #ccc; }}
  table {{ border-collapse: collapse; font-size: 11px; white-space: nowrap; }}
  th, td {{ border: 1px solid #ddd; padding: 4px 6px; text-align: left; }}
  th {{ background: #1a1a2e; color: #eee; position: sticky; top: 0; z-index: 1; }}
  tr:nth-child(even) {{ background: #f8f8f8; }}
  tr.exec {{ background: #e8f5e9; }}
  tr.mon {{ background: #fff8e1; }}
  .meta {{ color: #666; margin-bottom: 1rem; }}
</style>
</head><body>
<h1>{html.escape(title)}</h1>
<p class="meta">{len(rows)} pairs · generated from batch analysis</p>
<div class="wrap"><table>
<thead><tr>{thead}</tr></thead>
<tbody>
{"".join(body_rows)}
</tbody></table></div>
</body></html>"""
  Path(path).write_text(doc)


def save_trade_setups_markdown(
  results: List[dict],
  path: str,
  title: str = "Trade Setups",
) -> None:
  """Human-readable trade setups table — visible in repo at reports/TRADE_SETUPS.md."""
  rows: List[dict] = []
  for r in results:
    rows.extend(build_setup_rows(r))

  active = [r for r in rows if r.get("status") in ("executable", "monitor")]
  all_rows = active if active else [r for r in rows if r.get("status") != "error"]

  ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
  lines = [
    f"# {title}",
    "",
    f"Updated: **{ts}** · {len(results)} pairs · {len(all_rows)} setup rows",
    "",
    "> Full interactive table: `output/latest_analysis.html` (after batch run)",
    "> CSV: `output/latest_setups.csv`",
    "",
    "## Trade setups (scalp / day / swing / long-term)",
    "",
    "| Symbol | Price | Style | Status | Dir | Entry | Stop | TP1 | TP2 | RR | Harmonic | Reason |",
    "|--------|-------|-------|--------|-----|-------|------|-----|-----|-----|----------|--------|",
  ]

  def _cell(v: Any, n: int = 40) -> str:
    if v is None:
      return ""
    s = str(v).replace("|", "/")
    return s[:n] + ("…" if len(s) > n else "")

  for r in sorted(all_rows, key=lambda x: (x.get("symbol", ""), x.get("style", ""))):
    lines.append(
      f"| {r.get('symbol', '')} | {r.get('price', '')} | {r.get('style', '')} | "
      f"{r.get('status', '')} | {r.get('direction', '')} | {r.get('entry', '')} | "
      f"{r.get('stop_loss', '')} | {r.get('tp1', '')} | {r.get('tp2', '')} | "
      f"{r.get('rr_tp2', '')} | {_cell(r.get('harmonic', ''), 20)} | "
      f"{_cell(r.get('honest_reason', ''), 50)} |"
    )

  lines.extend(["", "## Primary setup per pair", ""])
  lines.append("| Symbol | Price | Primary | Status | Dir | Verdict | Outcome summary |")
  lines.append("|--------|-------|---------|--------|-----|---------|-----------------|")

  for r in results:
    if r.get("status") == "incomplete":
      continue
    oc = r.get("step8_outcomes", {})
    hs = oc.get("honest_summary", {})
    price = r.get("step1_htf_bias", {}).get("wave_C_current", "")
    ex = r.get("executive_decision", {})
    lines.append(
      f"| {r.get('symbol', '')} | {price} | {hs.get('primary_style', '')} | "
      f"{hs.get('primary_status', '')} | {hs.get('primary_direction', '')} | "
      f"{ex.get('verdict', '')} | {_cell(hs.get('truth', ''), 60)} |"
    )

  Path(path).parent.mkdir(parents=True, exist_ok=True)
  Path(path).write_text("\n".join(lines) + "\n")


def export_all_reports(results: List[dict], prefix: str, title: str) -> dict:
  """Write full CSV, setups CSV, HTML, and reports/TRADE_SETUPS.md."""
  paths = {
    "full_csv": f"{prefix}.csv",
    "setups_csv": f"{prefix.replace('_full_', '_setups_')}.csv",
    "full_html": f"{prefix}.html",
    "setups_md": "reports/TRADE_SETUPS.md",
  }
  save_full_csv(results, paths["full_csv"])
  save_setups_csv(results, paths["setups_csv"])
  save_full_html(results, paths["full_html"], title=title)
  save_trade_setups_markdown(results, paths["setups_md"], title=title.replace("— Full Analysis", "— Trade Setups"))
  return paths


def regenerate_from_json(json_path: str, output_dir: str = "output") -> dict:
  """Rebuild full reports from saved analysis JSON (if step8 missing, outcomes columns empty)."""
  results = json.loads(Path(json_path).read_text())
  stem = Path(json_path).stem.replace("_analysis", "_full")
  prefix = str(Path(output_dir) / stem)
  n = len(results)
  paths = export_all_reports(results, prefix, title=f"Top {n} Crypto — Trade Setups")
  paths["source_json"] = json_path
  paths["pairs"] = n
  paths["has_step8"] = sum(1 for r in results if r.get("step8_outcomes")) 
  return paths
