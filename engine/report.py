"""Detailed batch reports — waves, harmonics, setups per timeframe."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def _fmt_wave_sizes(sizes: dict) -> str:
  if not sizes:
    return ""
  return "|".join(f"{k}:{v}" for k, v in sizes.items())


def _fmt_harmonics(patterns: List[dict], max_n: int = 3) -> str:
  if not patterns:
    return ""
  parts = []
  for p in patterns[:max_n]:
    parts.append(f"{p['tf']}:{p['pattern']}@{p['prz_low']:.4g}-{p['prz_high']:.4g}")
  return "; ".join(parts)


def _tf_column(result: dict, tf: str, field: str) -> str:
  ws = result.get("step2_wave_structure", {}).get(tf, {}) or {}
  if field == "structure":
    return ws.get("structure", "")
  if field == "direction":
    return ws.get("direction", "")
  if field == "valid":
    return "Y" if ws.get("impulse_valid") else "N"
  if field == "violations":
    v = ws.get("violations", [])
    return v[0] if v else ""
  if field == "sizes":
    return _fmt_wave_sizes(ws.get("wave_sizes", {}))
  if field == "abc":
    a = ws.get("abc")
    if not a:
      return ""
    return f"B{a['wave_B_retrace_pct']}% C{a['wave_C_progress_pct']}%"
  return ""


def build_detailed_row(result: dict) -> dict:
  if result.get("status") == "incomplete" or not result.get("step1_htf_bias"):
    return {
      "symbol": result.get("symbol"),
      "error": result.get("error", "unknown"),
      "status": "incomplete",
    }

  htf = result.get("step1_htf_bias", {})
  kz = result.get("step3_kill_zone", {})
  ts = result.get("trade_setup", {})
  ex = result.get("executive_decision", {})
  cons = result.get("step6_wave_consensus", {})
  harm = result.get("step4_harmonic_scan", {})
  c_tgt = result.get("step3_c_targets", {})
  exec_v = result.get("step5_execution_validation", {})
  price = htf.get("wave_C_current", "")

  all_h = []
  for tf, scan in harm.items():
    all_h.extend(scan.get("patterns", [])[:2])

  row = {
    "symbol": result.get("symbol"),
    "price": round(price, 4) if price else "",
    "htf_state": htf.get("state"),
    "htf_bias": htf.get("bias"),
    "wave_A": f"{htf.get('wave_A', {}).get('type')} {htf.get('wave_A', {}).get('start'):.4g}→{htf.get('wave_A', {}).get('end'):.4g}" if htf.get("wave_A") else "",
    "B_end": htf.get("wave_B_end"),
    "c_target_100": round(c_tgt.get("c_target_100", 0), 4) if c_tgt else "",
    "c_target_161": round(c_tgt.get("c_target_161", 0), 4) if c_tgt else "",
    "kill_zone_low": round(kz.get("price_low", 0), 4),
    "kill_zone_high": round(kz.get("price_high", 0), 4),
    "kz_dist_pct": kz.get("cluster_meta", {}).get("distance_pct", ""),
    "in_kill_zone": "Y" if exec_v.get("in_zone") else "N",
    "harmonics_all": _fmt_harmonics(all_h, 5),
    "harmonics_in_zone": _fmt_harmonics(result.get("step4_harmonic_overlap", []), 3),
    "verdict": ex.get("verdict"),
    "action": ts.get("action"),
    "direction": ex.get("direction"),
    "entry_low": (ts.get("entry_zone") or [None])[0],
    "entry_high": (ts.get("entry_zone") or [None, None])[1] if ts.get("entry_zone") else "",
    "stop_loss": ts.get("stop_loss"),
    "take_profit_1": ts.get("take_profit_1"),
    "take_profit_2": ts.get("take_profit_2"),
    "risk_reward": ts.get("risk_reward"),
    "confidence": ts.get("confidence"),
    "consensus": cons.get("consensus_direction"),
    "agreement_pct": cons.get("agreement_pct"),
    "expert_direction": result.get("step6c_expert_direction", {}).get("direction"),
    "expert_confidence": result.get("step6c_expert_direction", {}).get("confidence"),
    "sentinel_direction": result.get("step6d_sentinel_analysis", {}).get("direction"),
    "sentinel_confidence": result.get("step6d_sentinel_analysis", {}).get("confidence"),
    "ehlers_phase_deg": result.get("step6b_cycle_confluence", {}).get("primary_ehlers_phase"),
    "expert_method": result.get("step6c_expert_direction", {}).get("method"),
    "hurst_regime": result.get("step6b_cycle_confluence", {}).get("primary_regime"),
    "hurst_exponent": result.get("step6b_cycle_confluence", {}).get("primary_hurst"),
    "cycle_period": result.get("step6b_cycle_confluence", {}).get("primary_period"),
    "cycle_phase": result.get("step6b_cycle_confluence", {}).get("primary_phase"),
    "cycle_direction": result.get("step6b_cycle_confluence", {}).get("cycle_direction"),
    "15m_valid": "Y" if exec_v.get("passes") else "N",
    "15m_violations": "|".join(exec_v.get("violations_sample", [])[:2]),
  }

  for tf in ["1w", "1d", "4h", "1h", "15m"]:
    row[f"{tf}_structure"] = _tf_column(result, tf, "structure")
    row[f"{tf}_dir"] = _tf_column(result, tf, "direction")
    row[f"{tf}_valid"] = _tf_column(result, tf, "valid")
    row[f"{tf}_W"] = _tf_column(result, tf, "sizes")
    row[f"{tf}_abc"] = _tf_column(result, tf, "abc")

  return row


def save_detailed_csv(results: List[dict], path: str) -> None:
  rows = [build_detailed_row(r) for r in results]
  rows = [r for r in rows if r]
  if not rows:
    return
  all_keys: list[str] = []
  seen = set()
  for row in rows:
    for k in row:
      if k not in seen:
        seen.add(k)
        all_keys.append(k)
  with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)


def save_detailed_markdown(results: List[dict], path: str, title: str = "Trading Analysis Report") -> None:
  lines = [f"# {title}", "", "| Symbol | Price | HTF | 1D Structure | 4H | 1H | 15m | Harmonics | Action | Entry | Stop | TP1 | RR |", "|--------|-------|-----|--------------|----|----|-----|-----------|--------|-------|------|-----|-----|"]

  for r in results:
    if r.get("status") == "incomplete":
      lines.append(f"| {r.get('symbol')} | ERROR | | | | | | | | | | | |")
      continue
    row = build_detailed_row(r)
    lines.append(
      f"| {row['symbol']} | {row['price']} | {row['htf_state']} | "
      f"{row.get('1d_structure', '')} | {row.get('4h_structure', '')} | {row.get('1h_structure', '')} | "
      f"{row.get('15m_structure', '')} | {row.get('harmonics_in_zone') or (row.get('harmonics_all') or '')[:40]} | "
      f"{row['action']} | {row['entry_low']}-{row['entry_high']} | {row['stop_loss']} | "
      f"{row['take_profit_1']} | {row['risk_reward']} |"
    )

  lines.append("")
  lines.append("## Per-symbol detail")
  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    lines.append(f"### {sym}")
    lines.append(f"- **HTF bias**: {r['step1_htf_bias']['state']} / {r['step1_htf_bias']['bias']}")
    kz = r["step3_kill_zone"]
    lines.append(f"- **Kill zone**: {kz['price_low']:.4g} – {kz['price_high']:.4g} ({kz.get('width_pct', 0):.1f}% wide)")
    ts = r["trade_setup"]
    lines.append(f"- **Trade**: {ts['action']} | entry {ts.get('entry_zone')} | SL {ts.get('stop_loss')} | TP1 {ts.get('take_profit_1')}")
    for tf in ["1w", "1d", "4h", "1h", "15m"]:
      ws = r.get("step2_wave_structure", {}).get(tf)
      if ws:
        lines.append(
          f"- **{tf}**: {ws.get('structure', 'n/a')} {ws.get('direction', 'n/a')} "
          f"valid={ws.get('impulse_valid', False)} sizes={ws.get('wave_sizes', {})}"
        )
    harm = r.get("step4_harmonic_scan", {})
    for tf, scan in harm.items():
      for p in scan.get("patterns", [])[:2]:
        lines.append(f"- **Harmonic {tf}**: {p['pattern']} PRZ {p['prz_low']:.4g}-{p['prz_high']:.4g} dist={p.get('dist_from_price_pct')}%")
    lines.append("")

  Path(path).write_text("\n".join(lines))


def save_wave_json_per_symbol(results: List[dict], out_dir: str) -> None:
  d = Path(out_dir)
  d.mkdir(parents=True, exist_ok=True)
  for r in results:
    sym = r.get("symbol", "unknown").replace("/", "_")
    with open(d / f"{sym}_waves.json", "w") as f:
      json.dump(
        {
          "symbol": r.get("symbol"),
          "wave_structure": r.get("step2_wave_structure"),
          "harmonics": r.get("step4_harmonic_scan"),
          "trade_setup": r.get("trade_setup"),
        },
        f,
        indent=2,
        default=str,
      )
