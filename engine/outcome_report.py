"""Outcome table export — honest executable setups per style."""

from __future__ import annotations

import csv
from typing import List


def build_outcome_row(result: dict) -> List[dict]:
  """One row per style (scalp, day_trade, swing, long_term)."""
  if result.get("status") == "incomplete":
    return [{"symbol": result.get("symbol"), "style": "—", "status": "error", "error": result.get("error")}]

  oc = result.get("step8_outcomes", {})
  hs = oc.get("honest_summary", {})
  rows = []
  for style in ("scalp", "day_trade", "swing", "long_term"):
    s = oc.get("setups", {}).get(style, {})
    if not s:
      continue
    targets = s.get("targets") or []
    dca = s.get("dca") or []
    ad = (oc.get("autodream") or {}).get("by_style", {}).get(style, {})
    rows.append({
      "symbol": result["symbol"],
      "price": result.get("step1_htf_bias", {}).get("wave_C_current"),
      "primary": "Y" if hs.get("primary_style") == style else "",
      "style": style,
      "timeframe": s.get("timeframe"),
      "horizon": s.get("horizon"),
      "status": s.get("status"),
      "execution_tier": s.get("execution_tier", ""),
      "readiness_score": s.get("readiness_score"),
      "indicator_signals": "; ".join(s.get("indicator_signals", [])[:3]),
      "zone_dist_pct": s.get("zone_dist_pct"),
      "direction": s.get("direction"),
      "honest_reason": s.get("honest_reason"),
      "wave_structure": s.get("wave_structure"),
      "wave_valid": "Y" if s.get("wave_valid") else "N",
      "entry": s.get("entry", {}).get("anchor"),
      "entry_zone_low": (s.get("entry", {}).get("zone") or [None])[0],
      "entry_zone_high": (s.get("entry", {}).get("zone") or [None, None])[1],
      "dca_10pct": dca[0]["price"] if len(dca) > 0 else "",
      "dca_20pct": dca[1]["price"] if len(dca) > 1 else "",
      "dca_30pct": dca[2]["price"] if len(dca) > 2 else "",
      "dca_40pct": dca[3]["price"] if len(dca) > 3 else "",
      "stop_loss": s.get("stop_loss", {}).get("price"),
      "stop_rule": s.get("stop_loss", {}).get("rule"),
      "tp1": targets[0]["price"] if len(targets) > 0 else "",
      "tp2": targets[1]["price"] if len(targets) > 1 else "",
      "tp3": targets[2]["price"] if len(targets) > 2 else "",
      "rr_tp2": targets[1]["rr"] if len(targets) > 1 else "",
      "account_risk_pct": s.get("risk", {}).get("account_risk_pct"),
      "harmonic": f"{s['harmonic']['pattern']}@{s['harmonic']['prz_low']:.4g}" if s.get("harmonic") else "",
      "hist_win_rate": s.get("historical_edge") or ad.get("win_rate"),
      "hist_trades": s.get("hist_trades") or ad.get("simulated_trades"),
      "hist_avg_pnl_r": s.get("hist_avg_pnl_r") or ad.get("avg_pnl_r"),
      "oos_win_rate": s.get("oos_win_rate") or ad.get("oos_win_rate"),
      "oos_trades": s.get("oos_trades") or ad.get("oos_trades"),
      "wf_degradation": s.get("wf_degradation") or ad.get("wf_degradation"),
      "stress_win_rate": s.get("stress_win_rate") or ad.get("stress_win_rate"),
      "mc_win_rate_p5": s.get("mc_win_rate_p5") or ad.get("mc_win_rate_p5"),
      "validation_summary": s.get("validation_summary") or ad.get("validation_summary"),
      "paper_outcome": s.get("paper_outcome"),
      "paper_pnl_r": s.get("paper_pnl_r"),
      "autodream_verdict": s.get("autodream_verdict"),
      "autodream_lesson": "; ".join(ad.get("lessons", [])[:1]) or s.get("confidence_note", "")[:80],
      "loss_lesson": s.get("loss_lesson"),
      "hedge_plan": (
        f"{s['hedge_plan']['hedge_size_pct']}% {s['hedge_plan']['hedge_direction']} "
        f"{s['hedge_plan']['hedge_instrument']}"
        if s.get("hedge_plan", {}).get("required") else ""
      ),
      "adjusted_risk_pct": (s.get("risk") or {}).get("account_risk_pct"),
    })
  return rows


def save_outcomes_csv(results: List[dict], path: str) -> None:
  rows: List[dict] = []
  for r in results:
    rows.extend(build_outcome_row(r))
  if not rows:
    return
  keys: list[str] = []
  seen = set()
  for row in rows:
    for k in row:
      if k not in seen:
        seen.add(k)
        keys.append(k)
  with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
