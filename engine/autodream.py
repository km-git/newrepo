"""Autodream: historical outcome tracking, monitoring, continuous improvement."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.paper_trading import (
  PAPER_METRICS_PATH,
  apply_honesty_adjustments,
  backtest_setup_on_bars,
  save_paper_metrics,
)
from engine.trade_learning import LEARNING_STATE_PATH, apply_learning_to_outcomes

HISTORY_PATH = Path("output/autodream/history.jsonl")
METRICS_PATH = Path("output/autodream/metrics.json")


def _load_history(limit: int = 5000) -> List[dict]:
  if not HISTORY_PATH.exists():
    return []
  rows = []
  with HISTORY_PATH.open() as f:
    for line in f:
      line = line.strip()
      if line:
        try:
          rows.append(json.loads(line))
        except json.JSONDecodeError:
          continue
  return rows[-limit:]


def record_outcome(symbol: str, outcomes: dict, price: float, pipeline_status: str) -> None:
  """Append run to historical log for continuous learning."""
  HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
  entry = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "symbol": symbol,
    "price": price,
    "pipeline_status": pipeline_status,
    "honest_summary": outcomes.get("honest_summary", {}),
    "setups": {
      k: {
        "status": v.get("status"),
        "direction": v.get("direction"),
        "entry": v.get("entry", {}).get("anchor"),
        "stop": v.get("stop_loss", {}).get("price"),
        "tp1": (v.get("targets") or [{}])[0].get("price") if v.get("targets") else None,
        "rr": (v.get("targets") or [{}, {}])[1].get("rr") if v.get("targets") and len(v["targets"]) > 1 else None,
        "paper_outcome": v.get("paper_outcome"),
        "paper_pnl_r": v.get("paper_pnl_r"),
        "autodream_verdict": v.get("autodream_verdict"),
      }
      for k, v in outcomes.get("setups", {}).items()
    },
  }
  with HISTORY_PATH.open("a") as f:
    f.write(json.dumps(entry, default=str) + "\n")


def analyze_historical(
  symbol: str,
  style: str,
  data_df,
  lookback_bars: int = 60,
  setup: Optional[dict] = None,
) -> dict:
  """
  Setup-faithful backtest on recent history when setup geometry is available.
  Falls back to style ATR geometry with setup direction.
  """
  if data_df is None or len(data_df) < 20:
    return {"available": False, "reason": "insufficient history"}

  if setup and setup.get("stop_loss") and setup.get("targets"):
    setup = {**setup, "style": style}
    result = backtest_setup_on_bars(data_df, setup, lookback_bars=lookback_bars, full_validation=True)
  else:
    result = _fallback_style_backtest(data_df, style, lookback_bars, setup)

  if not result.get("available"):
    return result

  hist = _load_history()
  sym_hist = [h for h in hist if h.get("symbol") == symbol]
  style_hist = []
  for h in sym_hist:
    s = h.get("setups", {}).get(style, {})
    if s:
      style_hist.append(s)

  win_rate = result.get("win_rate")
  total = result.get("simulated_trades", 0)

  return {
    **result,
    "style": style,
    "symbol": symbol,
    "logged_setups": len(style_hist),
    "confidence_adjustment": round((win_rate - 0.5) * 0.1, 3) if win_rate is not None else 0,
    "lessons": _lessons(win_rate, style_hist, style, total, result.get("avg_pnl_r")),
    "next_review_utc": datetime.now(timezone.utc).isoformat(),
  }


def _fallback_style_backtest(
  data_df,
  style: str,
  lookback_bars: int,
  setup: Optional[dict],
) -> dict:
  """Style-config ATR geometry using setup direction when present."""
  from core.atr import compute_atr14
  from engine.outcomes import STYLE_CONFIG
  from engine.trade_simulation import simulate_forward

  cfg = STYLE_CONFIG.get(style, STYLE_CONFIG["swing"])
  direction = (setup or {}).get("direction", "LONG")
  atr_mult = cfg["atr_mult_sl"]

  closes = data_df["Close"].values.astype(float)
  highs = data_df["High"].values.astype(float)
  lows = data_df["Low"].values.astype(float)
  atr = compute_atr14(data_df)

  wins = losses = 0
  pnl_sum = 0.0
  n = min(lookback_bars, len(closes) - 5)
  long = direction == "LONG"
  for i in range(len(closes) - n, len(closes) - 5):
    entry = closes[i]
    if long:
      stop = entry - atr * atr_mult
      tps = [{"price": entry + atr * 1.5, "exit_pct": 40, "rr": 1.5},
             {"price": entry + atr * 3.0, "exit_pct": 30, "rr": 3.0},
             {"price": entry + atr * 5.0, "exit_pct": 30, "rr": 5.0}]
    else:
      stop = entry + atr * atr_mult
      tps = [{"price": entry - atr * 1.5, "exit_pct": 40, "rr": 1.5},
             {"price": entry - atr * 3.0, "exit_pct": 30, "rr": 3.0},
             {"price": entry - atr * 5.0, "exit_pct": 30, "rr": 5.0}]
    sub_h = highs[i + 1 : i + 6].tolist()
    sub_l = lows[i + 1 : i + 6].tolist()
    if not sub_h:
      continue
    sim = simulate_forward(sub_h, sub_l, entry, stop, tps, direction, 5)
    if sim["outcome"] == "win":
      wins += 1
      pnl_sum += sim["pnl_r"]
    elif sim["outcome"] == "loss":
      losses += 1
      pnl_sum += sim["pnl_r"]

  total = wins + losses
  return {
    "available": True,
    "backtest_bars": n,
    "simulated_trades": total,
    "win_rate": round(wins / total, 3) if total else None,
    "wins": wins,
    "losses": losses,
    "avg_pnl_r": round(pnl_sum / total, 3) if total else None,
    "method": "style_atr_fallback",
  }


def _lessons(
  win_rate: Optional[float],
  style_hist: List[dict],
  style: str,
  hist_trades: int,
  avg_pnl_r: Optional[float],
) -> List[str]:
  lessons = []
  if win_rate is not None and hist_trades >= 3:
    if win_rate >= 0.55:
      lessons.append(
        f"{style}: setup-faithful hist favors TP-before-SL ({win_rate:.0%}, {hist_trades} entries)"
      )
    elif win_rate < 0.45:
      lessons.append(
        f"{style}: hist win {win_rate:.0%} on {hist_trades} zone entries — tighten or wait"
      )
    if avg_pnl_r is not None:
      if avg_pnl_r > 0.3:
        lessons.append(f"{style}: avg +{avg_pnl_r:.2f}R per hist trade")
      elif avg_pnl_r < -0.2:
        lessons.append(f"{style}: avg {avg_pnl_r:.2f}R — negative expectancy")
  elif hist_trades < 3:
    lessons.append(f"{style}: insufficient zone entries ({hist_trades}) for hist confidence")

  if len(style_hist) >= 3:
    dirs = [h.get("direction") for h in style_hist[-5:]]
    if dirs and len(set(dirs)) == 1:
      lessons.append(f"Consistent {dirs[0]} bias over last {len(dirs)} logged runs")
    paper_outcomes = [h.get("paper_outcome") for h in style_hist[-5:] if h.get("paper_outcome")]
    if len(paper_outcomes) >= 2:
      wr = sum(1 for p in paper_outcomes if p == "win") / len(paper_outcomes)
      lessons.append(f"Recent paper log: {wr:.0%} wins over {len(paper_outcomes)} runs")
  return lessons


def _get_df(data: dict, tf: str, fallback: str = "1d"):
  """Safe DataFrame lookup — never use `or` on pandas objects."""
  df = data.get(tf)
  if df is not None and len(df) > 0:
    return df
  fb = data.get(fallback)
  return fb if fb is not None and len(fb) > 0 else None


def enrich_outcomes_with_autodream(
  outcomes: dict,
  symbol: str,
  data: dict,
) -> dict:
  """Add per-style historical analysis, honesty adjustments, and autodream block."""
  autodream_styles = {}
  setups = outcomes.get("setups", {})
  style_tf = {
    "scalp": "15m", "day_trade": "1h", "swing": "1d", "long_term": "1w", "smc": "15m",
  }
  for style in ("scalp", "day_trade", "swing", "long_term", "smc"):
    tf = style_tf.get(style, "1d")
    df = _get_df(data, tf, "1d")
    setup = setups.get(style, {})
    autodream_styles[style] = analyze_historical(symbol, style, df, setup=setup)

  for style, ad in autodream_styles.items():
    setup = setups.get(style, {})
    if not setup or setup.get("status") == "not_actionable":
      continue
    adj = ad.get("confidence_adjustment", 0) or 0
    setup["historical_edge"] = ad.get("win_rate")
    setup["hist_trades"] = ad.get("simulated_trades")
    setup["hist_avg_pnl_r"] = ad.get("avg_pnl_r")
    setup["oos_win_rate"] = ad.get("oos_win_rate")
    setup["oos_trades"] = ad.get("oos_trades")
    setup["wf_degradation"] = ad.get("wf_degradation")
    setup["stress_win_rate"] = ad.get("stress_win_rate")
    setup["mc_win_rate_p5"] = ad.get("mc_win_rate_p5")
    setup["validation_summary"] = ad.get("validation_summary")
    setup["confidence_note"] = (
      f"autodream adj {adj:+.2f} · IS={ad.get('win_rate')} · "
      f"OOS={ad.get('oos_win_rate')} · {ad.get('validation_summary', ad.get('method', ''))}"
    )

  outcomes["autodream"] = {
    "by_style": autodream_styles,
    "history_entries": len(_load_history()),
    "history_path": str(HISTORY_PATH),
    "paper_metrics_path": str(PAPER_METRICS_PATH),
    "improvement_loop": (
      "Walk-forward OOS + holdout + MC + stress → paper batch → honesty → monitor"
    ),
  }
  outcomes = apply_honesty_adjustments(outcomes)
  if LEARNING_STATE_PATH.exists():
    try:
      learning = json.loads(LEARNING_STATE_PATH.read_text())
      if learning.get("available"):
        outcomes = apply_learning_to_outcomes(outcomes, symbol, data, learning)
    except (json.JSONDecodeError, OSError):
      pass
  _save_metrics(autodream_styles, outcomes.get("honest_summary", {}))
  return outcomes


def _save_metrics(by_style: dict, summary: dict) -> None:
  """Persist rolling autodream metrics from per-style analysis."""
  METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
  rates = [v["win_rate"] for v in by_style.values() if v.get("win_rate") is not None]
  trades = sum(v.get("simulated_trades", 0) for v in by_style.values())
  doc = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "styles_analyzed": len(by_style),
    "total_hist_trades": trades,
    "avg_win_rate": round(sum(rates) / len(rates), 3) if rates else None,
    "executable_count": summary.get("executable_count"),
    "probe_count": summary.get("probe_executable_count"),
    "by_style": {
      k: {
        "win_rate": v.get("win_rate"),
        "simulated_trades": v.get("simulated_trades"),
        "avg_pnl_r": v.get("avg_pnl_r"),
        "method": v.get("method"),
      }
      for k, v in by_style.items()
    },
  }
  METRICS_PATH.write_text(json.dumps(doc, indent=2))


def build_monitor_queue(results: List[dict]) -> List[dict]:
  """Active setups to watch (executable + monitor)."""
  queue = []
  for r in results:
    if r.get("status") == "incomplete":
      continue
    oc = r.get("step8_outcomes", {})
    for style, setup in oc.get("setups", {}).items():
      if setup.get("status") in ("executable", "monitor"):
        zone = setup.get("entry", {}).get("zone")
        row = {
          "id": f"{r['symbol']}:{style}",
          "symbol": r["symbol"],
          "style": style,
          "status": setup["status"],
          "direction": setup.get("direction"),
          "entry": setup.get("entry", {}).get("anchor"),
          "entry_zone": zone,
          "stop": setup.get("stop_loss", {}).get("price"),
          "tp1": setup["targets"][0]["price"] if setup.get("targets") else None,
          "check": setup.get("monitor", {}).get("check_interval"),
          "upgrade_if": setup.get("monitor", {}).get("upgrade_if", []),
          "invalidate_if": setup.get("monitor", {}).get("invalidate_if", []),
          "autodream_verdict": setup.get("autodream_verdict"),
          "hist_win_rate": setup.get("historical_edge"),
          "last_scan": None,
        }
        if style == "smc":
          row.update({
            "timeframe": setup.get("timeframe", "15m"),
            "execution_tier": setup.get("execution_tier"),
            "entry_signal": setup.get("entry_signal"),
            "entry_probe": setup.get("entry_probe"),
            "entry_grade": setup.get("entry_grade"),
            "confluence_count": setup.get("confluence_count"),
            "msb_pass": setup.get("msb_pass"),
            "indicator_tokens": setup.get("indicator_signals") or (
              (setup.get("indicators") or {}).get("active_tokens")
            ),
            "oos_win_rate": setup.get("oos_win_rate"),
            "oos_trades": setup.get("oos_trades"),
            "institutional_score": setup.get("institutional_score"),
          })
        queue.append(row)
  return queue


def save_monitor_queue(queue: List[dict], path: str = "output/autodream/monitor_queue.json") -> None:
  Path(path).parent.mkdir(parents=True, exist_ok=True)
  with open(path, "w") as f:
    json.dump({"updated": datetime.now(timezone.utc).isoformat(), "queue": queue}, f, indent=2)
