"""SMC paper cohort — reduced-size forward paper on FULL + PROBE executables."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from engine.indicator_calibration import (
  _load_ledger,
  _trade_tokens,
  _wilson_lower,
  enrich_ledger_entry,
  load_calibration,
  run_calibration_accumulation_cycle,
)
from engine.paper_trading import append_paper_ledger, paper_trade_setup
from engine.trade_simulation import SMC_COHORT_SIZE

COHORT_PATH = Path("output/autodream/smc_paper_cohort.json")
COHORT_CSV_PATH = Path("output/latest_smc_paper_cohort.csv")
COHORT_LIFT_PATH = Path("output/autodream/smc_token_lift.json")

FOCUS_TOKENS = (
  "liquidity sweep",
  "VP filter pass",
  "MSB z-score pass",
  "MSB z-score weak",
  "liquidity sweep EQL",
  "liquidity sweep EQH",
)


def extract_smc_executables(results: List[dict]) -> List[dict]:
  """Pull SMC setups with status=executable (FULL + PROBE)."""
  rows: List[dict] = []
  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    setup = (r.get("step8_outcomes") or {}).get("setups", {}).get("smc")
    if not setup or setup.get("status") != "executable":
      continue
    tier = setup.get("execution_tier", "none")
    if tier not in ("full", "probe"):
      continue
    rows.append({
      "symbol": sym,
      "setup": {**setup, "style": "smc"},
      "execution_tier": tier,
      "entry_grade": setup.get("entry_grade"),
      "entry_signal": setup.get("entry_signal"),
      "entry_probe": setup.get("entry_probe"),
      "timeframe": setup.get("timeframe", "15m"),
      "direction": setup.get("direction"),
      "confluence_count": setup.get("confluence_count"),
      "institutional_score": setup.get("institutional_score"),
      "honest_reason": setup.get("honest_reason"),
    })
  rows.sort(key=lambda x: (
    0 if x["execution_tier"] == "full" else 1,
    -(x.get("institutional_score") or 0),
    x["symbol"],
  ))
  return rows


def _cohort_size(tier: str) -> float:
  return SMC_COHORT_SIZE.get(tier, 0.25)


def _fetch_symbol_data(symbol: str, tfs: List[str]) -> Dict[str, pd.DataFrame]:
  from fetchers import fetch
  return fetch(symbol, tfs, is_crypto=True)


def _focus_tokens_present(tokens: List[str]) -> Dict[str, bool]:
  present = {t: False for t in FOCUS_TOKENS}
  token_set = set(tokens)
  for t in FOCUS_TOKENS:
    if t in token_set:
      present[t] = True
  # liquidity sweep variants
  if any("liquidity sweep" in x for x in token_set):
    present["liquidity sweep"] = True
  return present


def analyze_focus_token_lift(
  ledger: Optional[List[dict]] = None,
  cohort_only: bool = True,
) -> dict:
  """Lift for focus SMC tokens vs baseline on closed SMC ledger trades."""
  ledger = ledger if ledger is not None else _load_ledger()
  closed = [
    t for t in ledger
    if t.get("paper_outcome") in ("win", "loss")
    and t.get("style") == "smc"
    and (not cohort_only or t.get("cohort") == "smc_paper")
  ]
  if len(closed) < 5:
    return {
      "available": False,
      "reason": f"need >=5 closed SMC cohort trades, have {len(closed)}",
      "closed_trades": len(closed),
    }

  baseline_wr = sum(1 for t in closed if t["paper_outcome"] == "win") / len(closed)
  lifts: Dict[str, dict] = {}

  for focus in FOCUS_TOKENS:
    with_t = []
    without_t = []
    for trade in closed:
      tokens = _trade_tokens(trade)
      has = focus in tokens or (
        focus == "liquidity sweep" and any("liquidity sweep" in x for x in tokens)
      )
      if has:
        with_t.append(trade)
      else:
        without_t.append(trade)
    if len(with_t) < 3:
      lifts[focus] = {"samples": len(with_t), "status": "insufficient"}
      continue
    wr = sum(1 for t in with_t if t["paper_outcome"] == "win") / len(with_t)
    wins = sum(1 for t in with_t if t["paper_outcome"] == "win")
    lifts[focus] = {
      "samples": len(with_t),
      "win_rate": round(wr, 3),
      "lift_vs_baseline": round(wr - baseline_wr, 3),
      "wilson_lb": round(_wilson_lower(wins, len(with_t)), 3),
      "without_samples": len(without_t),
      "status": "ok",
    }

  ranked = sorted(
    [(k, v) for k, v in lifts.items() if v.get("status") == "ok"],
    key=lambda x: x[1].get("lift_vs_baseline", 0),
    reverse=True,
  )
  return {
    "available": True,
    "closed_trades": len(closed),
    "baseline_win_rate": round(baseline_wr, 3),
    "focus_tokens": lifts,
    "ranked_by_lift": [{"token": k, **v} for k, v in ranked],
  }


def run_smc_paper_cohort(
  results: List[dict],
  fetch_missing: bool = True,
  tfs: Optional[List[str]] = None,
) -> dict:
  """
  Paper-trade SMC FULL (50% size) and PROBE (25% size) executables.
  Appends enriched rows to paper ledger for calibration learning.
  """
  tfs = tfs or ["15m", "1h", "4h", "1d", "1w"]
  cohort_id = f"smc_paper_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
  executables = extract_smc_executables(results)
  cal = load_calibration()
  trades: List[dict] = []
  data_cache: Dict[str, dict] = {}

  for row in executables:
    sym = row["symbol"]
    setup = row["setup"]
    tf = row["timeframe"] or "15m"
    tier = row["execution_tier"]
    size = _cohort_size(tier)

    if fetch_missing and sym not in data_cache:
      try:
        data_cache[sym] = _fetch_symbol_data(sym, tfs)
      except Exception as e:
        data_cache[sym] = {"_error": str(e)}

    data = data_cache.get(sym, {})
    df = data.get(tf) if isinstance(data, dict) else None
    if df is None or not hasattr(df, "__len__") or len(df) < 10:
      trades.append({
        "symbol": sym,
        "style": "smc",
        "cohort": "smc_paper",
        "cohort_id": cohort_id,
        "execution_tier": tier,
        "available": False,
        "reason": f"missing {tf} data",
      })
      continue

    paper = paper_trade_setup(sym, setup, df, size_override=size)
    paper["cohort"] = "smc_paper"
    paper["cohort_id"] = cohort_id
    paper["cohort_size_pct"] = round(size * 100, 1)
    paper["timeframe"] = tf
    paper["entry_grade"] = row.get("entry_grade")
    paper["entry_signal"] = row.get("entry_signal")
    paper["entry_probe"] = row.get("entry_probe")
    paper["confluence_count"] = row.get("confluence_count")
    paper["institutional_score"] = row.get("institutional_score")
    paper["honest_reason"] = (row.get("honest_reason") or "")[:160]
    paper["readiness_score"] = setup.get("readiness_score")
    paper = enrich_ledger_entry(paper, setup, cal)
    paper["focus_tokens"] = _focus_tokens_present(paper.get("indicator_tokens") or [])
    trades.append(paper)

  closed = [t for t in trades if t.get("paper_outcome") in ("win", "loss")]
  full_trades = [t for t in trades if t.get("execution_tier") == "full"]
  probe_trades = [t for t in trades if t.get("execution_tier") == "probe"]

  report = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "cohort_id": cohort_id,
    "cohort": "smc_paper",
    "size_policy": dict(SMC_COHORT_SIZE),
    "executables_found": len(executables),
    "papered": len([t for t in trades if t.get("available")]),
    "full_count": len(full_trades),
    "probe_count": len(probe_trades),
    "closed_trades": len(closed),
    "open_trades": len(trades) - len(closed),
    "win_rate": round(
      sum(1 for t in closed if t["paper_outcome"] == "win") / len(closed), 3
    ) if closed else None,
    "avg_pnl_r": round(
      sum(t.get("paper_pnl_r", 0) for t in trades) / len(trades), 3
    ) if trades else None,
    "trades": trades,
    "executables": [
      {
        "symbol": e["symbol"],
        "tier": e["execution_tier"],
        "grade": e.get("entry_grade"),
        "tf": e.get("timeframe"),
        "direction": e.get("direction"),
        "size_pct": round(_cohort_size(e["execution_tier"]) * 100, 1),
      }
      for e in executables
    ],
  }

  lift = analyze_focus_token_lift(cohort_only=False)
  report["token_lift_all_smc"] = lift
  report["token_lift"] = analyze_focus_token_lift(cohort_only=True)

  return report


def save_smc_cohort(report: dict) -> dict:
  """Persist cohort report, CSV, and token lift."""
  COHORT_PATH.parent.mkdir(parents=True, exist_ok=True)
  COHORT_PATH.write_text(json.dumps(report, indent=2, default=str))

  trades = report.get("trades", [])
  if trades:
    keys = list(trades[0].keys())
    COHORT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COHORT_CSV_PATH.open("w", newline="") as f:
      w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
      w.writeheader()
      w.writerows(trades)

  lift = report.get("token_lift_all_smc") or {}
  if lift.get("available"):
    COHORT_LIFT_PATH.write_text(json.dumps(lift, indent=2, default=str))

  return {
    "json": str(COHORT_PATH),
    "csv": str(COHORT_CSV_PATH),
    "lift": str(COHORT_LIFT_PATH) if lift.get("available") else None,
  }


def run_and_persist_smc_cohort(
  results: List[dict],
  fetch_missing: bool = True,
) -> dict:
  """Run cohort, append ledger, trigger calibration accumulation."""
  report = run_smc_paper_cohort(results, fetch_missing=fetch_missing)
  valid = [t for t in report.get("trades", []) if t.get("available")]
  if valid:
    append_paper_ledger(valid)
  paths = save_smc_cohort(report)
  acc = run_calibration_accumulation_cycle()
  report["paths"] = paths
  report["calibration_accumulation"] = acc
  COHORT_PATH.write_text(json.dumps(report, indent=2, default=str))
  return report
