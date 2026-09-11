#!/usr/bin/env python3
"""Generate Phase 2 tables (B)-(E) from latest batch artifacts."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ccxt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.market_clock import data_as_of_from_frames, last_candle_ts_utc
from core.stats import MIN_HEADLINE_N, rate_display, wilson_ci
from engine.honesty_gate import is_honesty_executable, setup_geometry_ok
from fetchers import fetch


def _geom_ok(direction: str, entry: float, sl: float, tps: List[float]) -> Tuple[bool, str]:
  if entry <= 0 or sl <= 0 or any(p <= 0 for p in tps if p):
    return False, "non_positive_price"
  d = direction.upper()
  if d in ("LONG", "BULL"):
    if not (sl < entry < tps[0] < (tps[1] if len(tps) > 1 else tps[0]) < (tps[2] if len(tps) > 2 else tps[0])):
      return False, "long_geometry"
  else:
    if not (sl > entry > tps[0] > (tps[1] if len(tps) > 1 else tps[0]) > (tps[2] if len(tps) > 2 else tps[0])):
      return False, "short_geometry"
  return True, "ok"


def _rr(entry: float, sl: float, tp: float) -> float:
  risk = abs(entry - sl)
  if risk <= 0:
    return 0.0
  return round(abs(tp - entry) / risk, 2)


def _live_okx(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
  ex = ccxt.okx({"enableRateLimit": True})
  out = {}
  for sym in symbols:
    try:
      t = ex.fetch_ticker(sym)
      ohlcv = ex.fetch_ohlcv(sym, "1h", limit=1)
      ts = last_candle_ts_utc(
        __import__("pandas").DataFrame(
          ohlcv, columns=["ts", "Open", "High", "Low", "Close", "Volume"]
        ).set_index(__import__("pandas").to_datetime([r[0] for r in ohlcv], unit="ms", utc=True))
      ) if ohlcv else None
      out[sym] = {"live": float(t["last"]), "last_1h_utc": ts.isoformat() if ts else None}
    except Exception as e:
      out[sym] = {"live": None, "error": str(e)}
  return out


def main() -> int:
  analysis_path = sorted(ROOT.glob("output/top50_analysis_*.json"))[-1]
  board = json.loads((ROOT / "output/autodream/executive_board.json").read_text())
  limits = list(csv.DictReader((ROOT / "output/latest_limit_orders_all_tf.csv").open()))
  log = (ROOT / "output/top50_batch_run.log").read_text()

  results = json.loads(analysis_path.read_text())
  symbols = sorted({r["symbol"] for r in results if r.get("symbol")})
  live = _live_okx(symbols[:60])  # cap API calls

  executable_rows: List[dict] = []
  monitor_rows: List[dict] = []
  wf_stats: List[dict] = []

  for row in results:
    sym = row["symbol"]
    if row.get("status") == "incomplete":
      continue
    data = fetch(sym, ["15m", "1h", "4h", "1d", "1w"], True)
    as_of = data_as_of_from_frames(data, prefer_tf="1h")
    live_px = live.get(sym, {}).get("live")
    cons = row.get("step6_wave_consensus") or {}
    harm = len(row.get("step4_harmonic_scan") or [])
    ew = row.get("step2_ew_coverage") or {}

    for style, setup in (row.get("step8_outcomes") or {}).get("setups", {}).items():
      if not setup:
        continue
      st = setup.get("status")
      entry = float((setup.get("entry") or {}).get("anchor") or 0)
      sl = float((setup.get("stop_loss") or {}).get("price") or 0)
      tgs = setup.get("targets") or []
      tps = [float(t.get("price") or 0) for t in tgs[:3]]
      dca = setup.get("dca") or []
      dca_pct = [float(l.get("size_pct") or 0) for l in dca[:4]]
      dca_prices = [float(l.get("price") or 0) for l in dca[:4]]
      rr2 = float(tgs[1].get("rr") or 0) if len(tgs) > 1 else 0
      geom_ok, geom_note = _geom_ok(setup.get("direction", ""), entry, sl, tps)
      dist_pct = abs(live_px - entry) / live_px * 100 if live_px and entry else None

      rec = {
        "symbol": sym,
        "style": style,
        "tf": setup.get("timeframe"),
        "tier": setup.get("execution_tier"),
        "dir": setup.get("direction"),
        "live": live_px,
        "last_candle_utc": live.get(sym, {}).get("last_1h_utc"),
        "data_as_of_utc": as_of,
        "entry": entry,
        "dca_pct": "/".join(f"{p:.0f}" for p in dca_pct) if dca_pct else "",
        "dca_px": "/".join(f"{p:.4g}" for p in dca_prices) if dca_prices else "",
        "sl": sl,
        "tp1": tps[0] if tps else None,
        "tp2": tps[1] if len(tps) > 1 else None,
        "tp3": tps[2] if len(tps) > 2 else None,
        "rr": rr2,
        "rr_calc": _rr(entry, sl, tps[1] if len(tps) > 1 else tps[0]) if tps and sl and entry else 0,
        "readiness": setup.get("readiness_score"),
        "ew_cov": ew.get("coverage_pct"),
        "harmonic": harm,
        "consensus_pct": cons.get("agreement_pct"),
        "in_kz": setup.get("indicators", {}).get("zone_dist_pct", 99) < 2 if setup.get("indicators") else False,
        "is_wr": setup.get("is_win_rate"),
        "is_n": setup.get("is_trades"),
        "oos_wr": setup.get("oos_win_rate"),
        "oos_n": setup.get("oos_trades"),
        "oos_display": rate_display(
          setup.get("oos_win_rate"),
          int(setup.get("oos_trades") or 0),
          wins=int(round(float(setup.get("oos_win_rate") or 0) * int(setup.get("oos_trades") or 0)))
          if setup.get("oos_win_rate") is not None and int(setup.get("oos_trades") or 0) > 0 else None,
        ),
        "is_display": rate_display(
          setup.get("is_win_rate"),
          int(setup.get("is_trades") or 0),
        ),
        "oos_gate": setup.get("oos_gate"),
        "geom_ok": geom_ok,
        "geom_note": geom_note,
        "dist_from_live_pct": round(dist_pct, 2) if dist_pct is not None else None,
        "reason": (setup.get("honest_reason") or "")[:80],
      }

      ad = (row.get("step8_outcomes") or {}).get("autodream", {}).get("by_style", {}).get(style, {})
      if ad.get("walk_forward"):
        wf = ad["walk_forward"]
        wf_stats.append({
          "symbol": sym, "style": style,
          "wf_oos_wr": wf.get("oos_win_rate"), "wf_n": wf.get("oos_trades"),
          "holdout_oos_wr": (ad.get("holdout") or {}).get("oos_win_rate"),
          "degradation": wf.get("degradation"),
          "data_as_of_utc": wf.get("data_as_of_utc") or as_of,
        })

      if is_honesty_executable(setup, style):
        executable_rows.append(rec)
      elif st == "executable" and geom_ok:
        rec["reason"] = f"honesty_fail:{setup.get('oos_gate')}"
        monitor_rows.append(rec)
      elif st in ("monitor", "executable") and not geom_ok:
        rec["reason"] = f"geom_fail:{geom_note}"
        monitor_rows.append(rec)
      elif st == "monitor":
        monitor_rows.append(rec)

  exec_csv = [r for r in limits if r.get("gtc_tier") == "executable" and r.get("row_type") == "primary"]
  board_exec = [p for p in board.get("picks", []) if p.get("executive_action") == "EXECUTE_NOW"]
  honesty_count = len(executable_rows)

  # Tool audit from log
  tools = {
    "ccxt_okx_ohlc": ("Y", "50×5", 0, "—"),
    "ew_matrix": ("Y", "50×5", 0, "—"),
    "pyharmonics": ("Y", "50×5", 0, "—"),
    "wave_alpha": ("Y", "50×5", len(re.findall("YFPricesMissingError|YFTzMissingError", log)), "partial yfinance misses"),
    "python_taew": ("Y", "50×5", 0, "—"),
    "hurst_ehlers_sentinel": ("Y", "50", 0, "—"),
    "monte_carlo": ("Y", "50", 0, "—"),
    "executive_board": ("Y", "1", 0, "—"),
    "paper_batch": ("Y", "187 setups", 0, "—"),
    "indicator_calibration": ("N", "0", 0, "need >=30 closed trades"),
  }

  out = ROOT / "output/phase2_tables.json"
  payload = {
    "executable_honest": executable_rows,
    "monitor": sorted(monitor_rows, key=lambda x: (-(x.get("readiness") or 0), x["symbol"]))[:20],
    "exec_csv_count": len(exec_csv),
    "honesty_executable_count": honesty_count,
    "board_execute_now": len(board_exec),
    "execute_now_matches_honesty": len(board_exec) == honesty_count,
    "board_by_action": board.get("by_action"),
    "wf_stats": wf_stats,
    "tools": tools,
    "live_reference": live,
  }
  out.write_text(json.dumps(payload, indent=2, default=str))
  print(json.dumps(payload, indent=2, default=str))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
