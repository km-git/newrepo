"""Score and rank honest trade setups across all pairs and style timeframes."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.risk import MAX_STOP_PCT

STYLE_TF = {
  "scalp": "15m",
  "day_trade": "1h",
  "swing": "1d",
  "long_term": "1w",
  "smc": "15m",
}

MIN_OOS_TRADES = 3
MIN_OOS_ACCURATE = 0.55
MIN_OOS_HIGH = 0.65


def _stop_ok(setup: dict, style: str) -> bool:
  entry = (setup.get("entry") or {}).get("anchor")
  if entry is not None:
    try:
      if float(entry) <= 0:
        return False
    except (TypeError, ValueError):
      return False
  stop_pct = (setup.get("stop_loss") or {}).get("distance_pct")
  if stop_pct is None:
    return True
  try:
    dist = abs(float(stop_pct))
    return dist <= MAX_STOP_PCT.get(style, 8.0) * 1.5
  except (TypeError, ValueError):
    return False


def score_setup_accuracy(setup: dict, style: str) -> Tuple[int, str, List[str]]:
  """
  Returns (score 0-100, tier, tags).
  Tiers: A=tradeable, B=high-confidence watch, C=validated monitor, D=weak, X=broken geometry
  """
  if not setup or setup.get("status") == "not_actionable":
    return 0, "D", ["not_actionable"]

  if not _stop_ok(setup, style):
    return 0, "X", ["broken_stop_geometry"]

  tags: List[str] = []
  score = 0
  oos = setup.get("oos_win_rate")
  oos_n = int(setup.get("oos_trades") or 0)
  status = setup.get("status")
  tier_exec = setup.get("execution_tier", "none")
  verdict = setup.get("autodream_verdict")
  readiness = int(setup.get("readiness_score") or 0)
  wave_valid = bool(setup.get("wave_valid"))
  oos_gate = setup.get("oos_gate")

  if status == "executable":
    score += 40
    tags.append("executable")
    if tier_exec == "full":
      score += 15
      tags.append("FULL")
    elif tier_exec == "probe":
      score += 8
      tags.append("PROBE")

  if oos_n >= MIN_OOS_TRADES and oos is not None:
    oos_f = float(oos)
    if oos_f >= MIN_OOS_HIGH:
      score += 35
      tags.append(f"OOS {oos_f:.0%}")
    elif oos_f >= MIN_OOS_ACCURATE:
      score += 25
      tags.append(f"OOS {oos_f:.0%}")
    elif oos_f >= 0.50:
      score += 10
      tags.append(f"OOS {oos_f:.0%}")

  if verdict == "validated":
    score += 15
    tags.append("validated")
  elif verdict == "caution":
    score -= 10
    tags.append("caution")

  if wave_valid:
    score += 10
    tags.append("impulse_valid")

  # SMC institutional edge (Phases 1–5)
  if setup.get("entry_signal"):
    score += 18
    tags.append("smc_entry_signal")
  elif setup.get("entry_probe"):
    score += 12
    tags.append("smc_entry_probe")
  elif setup.get("smc_valid"):
    score += 10
    tags.append("smc_valid")
  entry_grade = setup.get("entry_grade")
  if entry_grade == "A":
    score += 12
    tags.append("smc_grade_A")
  elif entry_grade == "B":
    score += 6
    tags.append("smc_grade_B")
  conf = int(setup.get("confluence_count") or 0)
  if conf >= 3:
    score += 8
    tags.append("smc_confluence_3")
  elif conf >= 2:
    score += 4
    tags.append("smc_confluence_2")

  if readiness >= 72:
    score += 8
  elif readiness >= 65:
    score += 5

  if oos_gate == "passed":
    score += 10
    tags.append("oos_gate_passed")
  elif oos_gate == "below_threshold":
    score -= 20
    tags.append("oos_gate_fail")

  stress = setup.get("stress_win_rate")
  if stress is not None and float(stress) >= 0.55:
    score += 5

  mc = setup.get("mc_win_rate_p5")
  if mc is not None and float(mc) >= 0.50:
    score += 3

  paper = setup.get("paper_outcome")
  if paper == "win":
    score += 3
  elif paper == "loss":
    score -= 2

  # Tier assignment
  if status == "executable" and oos_gate == "passed":
    acc_tier = "A"
  elif score >= 70 and oos_n >= MIN_OOS_TRADES and oos is not None and float(oos) >= MIN_OOS_HIGH:
    acc_tier = "A" if wave_valid else "B"
  elif score >= 55 and oos_n >= MIN_OOS_TRADES and oos is not None and float(oos) >= MIN_OOS_ACCURATE:
    acc_tier = "B" if wave_valid or readiness >= 60 else "C"
  elif score >= 40 and verdict == "validated":
    acc_tier = "C"
  else:
    acc_tier = "D"

  return min(100, max(0, score)), acc_tier, tags


def extract_accurate_setups(results: List[dict], min_tier: str = "C") -> List[dict]:
  """Flatten batch results into scored setup rows."""
  tier_order = {"A": 0, "B": 1, "C": 2, "D": 3, "X": 9}
  min_rank = tier_order.get(min_tier, 2)
  rows: List[dict] = []

  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    ex = r.get("executive_decision") or {}
    cons = r.get("step6_wave_consensus") or {}
    oc = r.get("step8_outcomes") or {}

    for style, setup in (oc.get("setups") or {}).items():
      if not setup:
        continue
      score, acc_tier, tags = score_setup_accuracy(setup, style)
      if tier_order.get(acc_tier, 9) > min_rank:
        continue

      targets = setup.get("targets") or []
      entry = setup.get("entry") or {}
      stop = setup.get("stop_loss") or {}

      rows.append({
        "accuracy_tier": acc_tier,
        "accuracy_score": score,
        "tags": ", ".join(tags),
        "symbol": sym,
        "style": style,
        "timeframe": STYLE_TF.get(style, setup.get("timeframe", "")),
        "entry_grade": setup.get("entry_grade"),
        "entry_signal": setup.get("entry_signal"),
        "confluence_count": setup.get("confluence_count"),
        "smc_valid": setup.get("smc_valid"),
        "horizon": setup.get("horizon", ""),
        "status": setup.get("status"),
        "execution_tier": setup.get("execution_tier", ""),
        "direction": setup.get("direction"),
        "readiness_score": setup.get("readiness_score"),
        "wave_structure": setup.get("wave_structure"),
        "wave_valid": setup.get("wave_valid"),
        "entry": entry.get("anchor"),
        "entry_order": entry.get("order_type"),
        "zone_low": (entry.get("zone") or [None])[0],
        "zone_high": (entry.get("zone") or [None, None])[1],
        "stop_loss": stop.get("price"),
        "stop_pct": stop.get("distance_pct"),
        "tp1": targets[0]["price"] if targets else None,
        "tp2": targets[1]["price"] if len(targets) > 1 else None,
        "rr_tp2": targets[1]["rr"] if len(targets) > 1 else None,
        "oos_win_rate": setup.get("oos_win_rate"),
        "oos_trades": setup.get("oos_trades"),
        "hist_win_rate": setup.get("historical_edge"),
        "stress_win_rate": setup.get("stress_win_rate"),
        "mc_win_rate_p5": setup.get("mc_win_rate_p5"),
        "paper_outcome": setup.get("paper_outcome"),
        "paper_pnl_r": setup.get("paper_pnl_r"),
        "autodream_verdict": setup.get("autodream_verdict"),
        "oos_gate": setup.get("oos_gate"),
        "executive_verdict": ex.get("verdict"),
        "consensus": cons.get("consensus_direction"),
        "agreement_pct": cons.get("agreement_pct"),
        "honest_reason": (setup.get("honest_reason") or "")[:160],
        "validation_summary": setup.get("validation_summary"),
      })

  rows.sort(key=lambda x: (
    tier_order.get(x["accuracy_tier"], 9),
    -x["accuracy_score"],
    -(float(x["oos_win_rate"]) if x.get("oos_win_rate") is not None else 0),
    -int(x.get("readiness_score") or 0),
  ))
  return rows


def summarize_accurate(rows: List[dict]) -> dict:
  from collections import Counter

  by_tier = Counter(r["accuracy_tier"] for r in rows)
  by_style = Counter(r["style"] for r in rows)
  executable = [r for r in rows if r["status"] == "executable"]
  return {
    "total_accurate": len(rows),
    "by_tier": dict(by_tier),
    "by_style": dict(by_style),
    "executable_count": len(executable),
    "tier_a": [r for r in rows if r["accuracy_tier"] == "A"],
    "tier_b": [r for r in rows if r["accuracy_tier"] == "B"],
    "tier_c": [r for r in rows if r["accuracy_tier"] == "C"],
  }


def save_accurate_setups_csv(rows: List[dict], path: str | Path) -> str:
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  if not rows:
    path.write_text("")
    return str(path)
  keys = list(rows[0].keys())
  with path.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
  return str(path)


def load_results_json(path: str | Path) -> List[dict]:
  return json.loads(Path(path).read_text())


def find_latest_analysis_json(output_dir: str = "output") -> Optional[Path]:
  candidates = sorted(
    Path(output_dir).glob("top*_analysis_*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
  )
  for p in candidates:
    if "top50" in p.name:
      return p
  return candidates[0] if candidates else None


def _primary_blocker(setup: dict, style: str) -> str:
  reason = setup.get("honest_reason", "")
  if not _stop_ok(setup, style):
    return "broken_geometry"
  if setup.get("status") == "not_actionable":
    if "R:R" in reason and "below min" in reason:
      return "rr_below_min"
    if style == "smc" and setup.get("confluence_count", 0) >= 1:
      return "await_smc_confluence"
    return "no_edge"
  if setup.get("oos_gate") == "below_threshold":
    return "oos_below_floor"
  if setup.get("oos_gate") == "insufficient_oos":
    return "oos_insufficient"
  if style == "smc" and setup.get("status") == "monitor":
    return "await_smc_confluence"
  if "invalid_impulse" in reason and not setup.get("wave_partial"):
    return "invalid_impulse"
  if not setup.get("wave_valid") and setup.get("status") == "monitor":
    return "await_impulse_or_zone"
  if setup.get("status") == "executable":
    return "none"
  return "conditional"


def _research_tier(setup: dict, style: str, accuracy_tier: str) -> str:
  """Human-readable tier for all 200 setups."""
  if setup.get("status") == "executable":
    return "tradeable"
  if accuracy_tier in ("A", "B"):
    return "high_watch"
  if accuracy_tier == "C":
    return "validated_monitor"
  if setup.get("status") == "monitor":
    return "conditional"
  blocker = _primary_blocker(setup, style)
  if blocker == "rr_below_min" and _stop_ok(setup, style):
    return "speculative"
  return "skip"


def extract_research_setups(results: List[dict]) -> List[dict]:
  """All pair × timeframe rows with entry/stop/TP and honest research tier."""
  rows: List[dict] = []
  tier_order = {"tradeable": 0, "high_watch": 1, "validated_monitor": 2, "conditional": 3, "speculative": 4, "skip": 5}

  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    ex = r.get("executive_decision") or {}
    cons = r.get("step6_wave_consensus") or {}
    oc = r.get("step8_outcomes") or {}

    for style, setup in (oc.get("setups") or {}).items():
      if not setup:
        continue
      acc_score, acc_tier, tags = score_setup_accuracy(setup, style)
      research_tier = _research_tier(setup, style, acc_tier)
      targets = setup.get("targets") or []
      entry = setup.get("entry") or {}
      stop = setup.get("stop_loss") or {}

      rows.append({
        "research_tier": research_tier,
        "accuracy_tier": acc_tier,
        "accuracy_score": acc_score,
        "primary_blocker": _primary_blocker(setup, style),
        "tags": ", ".join(tags),
        "symbol": sym,
        "style": style,
        "timeframe": STYLE_TF.get(style, setup.get("timeframe", "")),
        "entry_grade": setup.get("entry_grade"),
        "entry_signal": setup.get("entry_signal"),
        "confluence_count": setup.get("confluence_count"),
        "smc_valid": setup.get("smc_valid"),
        "horizon": setup.get("horizon", ""),
        "pipeline_status": setup.get("status"),
        "execution_tier": setup.get("execution_tier", ""),
        "direction": setup.get("direction"),
        "readiness_score": setup.get("readiness_score"),
        "wave_structure": setup.get("wave_structure"),
        "wave_valid": setup.get("wave_valid"),
        "wave_partial": setup.get("wave_partial"),
        "entry": entry.get("anchor"),
        "entry_order": entry.get("order_type"),
        "zone_low": (entry.get("zone") or [None])[0],
        "zone_high": (entry.get("zone") or [None, None])[1],
        "stop_loss": stop.get("price"),
        "stop_pct": stop.get("distance_pct"),
        "tp1": targets[0]["price"] if targets else None,
        "tp2": targets[1]["price"] if len(targets) > 1 else None,
        "tp3": targets[2]["price"] if len(targets) > 2 else None,
        "rr_tp2": targets[1]["rr"] if len(targets) > 1 else None,
        "oos_win_rate": setup.get("oos_win_rate"),
        "oos_trades": setup.get("oos_trades"),
        "hist_win_rate": setup.get("historical_edge"),
        "stress_win_rate": setup.get("stress_win_rate"),
        "paper_outcome": setup.get("paper_outcome"),
        "autodream_verdict": setup.get("autodream_verdict"),
        "oos_gate": setup.get("oos_gate"),
        "executive_verdict": ex.get("verdict"),
        "consensus": cons.get("consensus_direction"),
        "honest_reason": (setup.get("honest_reason") or "")[:200],
      })

  rows.sort(key=lambda x: (
    tier_order.get(x["research_tier"], 9),
    -x["accuracy_score"],
    x["symbol"],
    x["style"],
  ))
  return rows


def summarize_research(rows: List[dict]) -> dict:
  from collections import Counter

  return {
    "total": len(rows),
    "by_research_tier": dict(Counter(r["research_tier"] for r in rows)),
    "by_timeframe": dict(Counter(r["timeframe"] for r in rows)),
    "by_pipeline_status": dict(Counter(r["pipeline_status"] for r in rows)),
    "tradeable": [r for r in rows if r["research_tier"] == "tradeable"],
    "high_watch": [r for r in rows if r["research_tier"] == "high_watch"],
  }


def save_research_setups_csv(rows: List[dict], path: str | Path) -> str:
  return save_accurate_setups_csv(rows, path)
