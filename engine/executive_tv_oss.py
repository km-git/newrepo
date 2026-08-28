"""
TradingView OSS + free-data layer for executive decision-making.

Scores direction-aware TV confluence (Supertrend, Chandelier, Hull MA, BB,
TTM Squeeze, ADX, RSI, VWAP + microstructure + cycles) and adjusts verdicts.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd

from core.tv_indicators import score_tv_confluence


def tv_oss_executive_enabled() -> bool:
  return os.environ.get("EW_TV_OSS_EXECUTIVE", "1").lower() not in ("0", "false", "no")


def _load_layer_weights() -> Dict[str, float]:
  try:
    from engine.tv_oss_consensus import load_tv_oss_consensus

    state = load_tv_oss_consensus()
    if state.get("layer_weights"):
      return state["layer_weights"]
  except Exception:
    pass
  raw = os.environ.get("EW_TV_LAYER_WEIGHTS", "")
  if raw.strip():
    try:
      import json

      return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
      pass
  return {}


def _direction_label(direction: str) -> str:
  d = (direction or "").upper()
  if d in ("LONG", "BULL"):
    return "LONG"
  if d in ("SHORT", "BEAR"):
    return "SHORT"
  return "LONG"


def ensure_tv_oss_consensus(*, use_llm: bool = False) -> dict:
  """Load or refresh TV OSS executive consensus (layer weights + active stack)."""
  if not tv_oss_executive_enabled():
    return {}
  try:
    from engine.tv_oss_consensus import load_tv_oss_consensus, run_tv_oss_consensus, tv_oss_consensus_enabled

    state = load_tv_oss_consensus()
    if state.get("layer_weights"):
      return state
    if tv_oss_consensus_enabled():
      return run_tv_oss_consensus(use_llm=use_llm)
  except Exception:
    pass
  return {}


def build_tv_executive_context(
  direction: str,
  data: Dict[str, pd.DataFrame],
  market_tools: Optional[dict] = None,
) -> Dict[str, Any]:
  """
  Aggregate TV OSS confluence + microstructure + cycles + web intel for executive use.
  """
  if not tv_oss_executive_enabled():
    return {"enabled": False}

  market_tools = market_tools or {}
  dir_label = _direction_label(direction)
  layer_weights = _load_layer_weights()
  consensus = ensure_tv_oss_consensus(use_llm=False)

  # Primary TF for TV scoring — prefer 1h execution, fall back to 4h/1d
  df = None
  for tf in ("1h", "4h", "15m", "1d"):
    candidate = data.get(tf)
    if candidate is not None and len(candidate) >= 30:
      df = candidate
      break

  ob = market_tools.get("orderbook")
  orderbook = ob if ob and ob.get("available") else None

  tv = market_tools.get("tv_confluence") or {}
  scored_dir = market_tools.get("scored_direction")
  if df is not None and (not tv or scored_dir != dir_label):
    tv = score_tv_confluence(df, dir_label, layer_weights=layer_weights, orderbook=orderbook)
  elif not tv and df is not None:
    tv = score_tv_confluence(df, dir_label, layer_weights=layer_weights, orderbook=orderbook)

  ms = market_tools.get("ms_confluence") or {}
  if (not ms or ms.get("score") is None) and df is not None:
    try:
      from core.tv_microstructure import compute_microstructure_signals, score_microstructure_confluence

      ms_raw = market_tools.get("microstructure") or compute_microstructure_signals(df, orderbook)
      ms = score_microstructure_confluence(ms_raw, dir_label)
    except Exception:
      ms = {"score": 50, "aligned": False, "signals": []}

  cyc = market_tools.get("cycle_confluence") or {}
  if (not cyc or cyc.get("score") is None) and df is not None:
    try:
      from core.tv_cycles import compute_cycle_signals, score_cycle_confluence

      cyc_raw = market_tools.get("cycles") or compute_cycle_signals(df)
      cyc = score_cycle_confluence(cyc_raw, dir_label)
    except Exception:
      cyc = {"score": 50, "aligned": False, "signals": [], "strategy_mode": "neutral"}

  web = market_tools.get("web_intel") or {}
  web_signals = list(web.get("signals") or [])[:6]

  # Composite executive score (TV primary, MS/cycle/web modifiers)
  tv_score = int(tv.get("score", 50))
  ms_score = int(ms.get("score", 50))
  cyc_score = int(cyc.get("score", 50))
  composite = int(tv_score * 0.55 + ms_score * 0.25 + cyc_score * 0.20)

  web_boost = 0
  fg = (web.get("fear_greed") or {})
  if fg.get("available"):
    val = fg.get("value", 50)
    if dir_label == "LONG" and val <= 30:
      web_boost += 5
    elif dir_label == "SHORT" and val >= 70:
      web_boost += 5
  funding_cross = web.get("funding_cross") or {}
  if funding_cross.get("available") and funding_cross.get("consensus_bias"):
    bias = funding_cross["consensus_bias"]
    if (dir_label == "LONG" and bias == "short_crowded") or (dir_label == "SHORT" and bias == "long_crowded"):
      web_boost += 4
  oi = web.get("open_interest") or {}
  if oi.get("available") and oi.get("oi_change_24h_pct") is not None:
    chg = oi["oi_change_24h_pct"]
    if abs(chg) > 5:
      web_boost += 2 if (dir_label == "LONG" and chg > 0) or (dir_label == "SHORT" and chg < 0) else -2

  composite = max(0, min(100, composite + web_boost))
  aligned = composite >= 58 and tv.get("aligned", composite >= 55)

  signals: List[str] = []
  signals.extend((tv.get("signals") or [])[:4])
  signals.extend((ms.get("signals") or [])[:2])
  signals.extend((cyc.get("signals") or [])[:2])
  signals.extend(web_signals[:3])

  return {
    "enabled": True,
    "direction": dir_label,
    "tv_score": tv_score,
    "ms_score": ms_score,
    "cycle_score": cyc_score,
    "composite_score": composite,
    "aligned": aligned,
    "opposes": composite < 42,
    "signals": signals[:10],
    "layer_weights": layer_weights,
    "active_indicators": consensus.get("active_indicators", [])[:6],
    "consensus_stance": consensus.get("consensus_stance"),
    "layers": tv.get("layers", {}),
    "strategy_mode": cyc.get("strategy_mode"),
    "web_boost": web_boost,
  }


_VERDICT_RANK = {
  "GO": 5,
  "CONDITIONAL_GO": 4,
  "STANDBY_ORDERS": 3,
  "STAGED_GO": 2,
  "NO_GO": 1,
  "WAIT": 1,
}

_RANK_VERDICT = {v: k for k, v in _VERDICT_RANK.items()}


def _shift_verdict(verdict: str, delta: int) -> str:
  rank = _VERDICT_RANK.get(verdict, 2)
  new_rank = max(1, min(5, rank + delta))
  return _RANK_VERDICT.get(new_rank, verdict)


def apply_tv_oss_to_decision(decision: dict, tv_ctx: dict) -> dict:
  """
  Adjust executive verdict, confidence, and position size using TV OSS composite.
  """
  if not tv_ctx.get("enabled"):
    return decision

  decision = dict(decision)
  executive = dict(decision.get("executive_decision") or {})
  trade = dict(decision.get("trade_setup") or {})

  verdict = executive.get("verdict", "STAGED_GO")
  draft_verdict = executive.get("draft_verdict", verdict)
  if "draft_verdict" not in executive:
    executive["draft_verdict"] = draft_verdict

  score = int(tv_ctx.get("composite_score", 50))
  aligned = tv_ctx.get("aligned", False)
  opposes = tv_ctx.get("opposes", False)
  size = int(executive.get("position_size_pct", 100))
  conf = float(trade.get("confidence", 0.5))

  gaps = list(executive.get("structural_gaps") or [])
  note = f"TV OSS composite {score}/100"
  if tv_ctx.get("active_indicators"):
    note += f" [{', '.join(tv_ctx['active_indicators'][:3])}]"

  if aligned and score >= 70:
    conf = min(0.92, conf + 0.08)
    size = min(100, size + 15)
    if verdict == "CONDITIONAL_GO":
      verdict = "GO"
      decision["status"] = "execute"
    elif verdict == "STAGED_GO" and score >= 75:
      verdict = "CONDITIONAL_GO"
    note += " — strong TV OSS alignment"
  elif aligned and score >= 62:
    conf = min(0.88, conf + 0.05)
    size = min(100, size + 8)
    note += " — TV OSS supports"
  elif opposes or score < 38:
    conf = max(0.25, conf - 0.10)
    size = max(25, size - 25)
    if verdict == "GO":
      verdict = "CONDITIONAL_GO"
      decision["status"] = "conditional_execute"
    elif verdict in ("CONDITIONAL_GO", "STANDBY_ORDERS"):
      verdict = _shift_verdict(verdict, -1)
    gaps.append(f"TV OSS opposes trade ({score}/100)")
    note += " — TV OSS divergence, reduce size"
  elif score < 48:
    conf = max(0.30, conf - 0.04)
    size = max(40, size - 10)
    note += " — mixed TV OSS"

  executive["verdict"] = verdict
  executive["position_size_pct"] = size
  executive["structural_gaps"] = gaps
  executive["tv_oss"] = {
    "composite_score": score,
    "tv_score": tv_ctx.get("tv_score"),
    "ms_score": tv_ctx.get("ms_score"),
    "cycle_score": tv_ctx.get("cycle_score"),
    "aligned": aligned,
    "opposes": opposes,
    "signals": tv_ctx.get("signals", [])[:6],
    "active_indicators": tv_ctx.get("active_indicators", []),
    "layer_weights": tv_ctx.get("layer_weights"),
    "strategy_mode": tv_ctx.get("strategy_mode"),
    "note": note,
  }
  trade["confidence"] = round(conf, 2)
  reason = trade.get("reason", "")
  trade["reason"] = f"{reason} | {note}" if reason else note

  decision["executive_decision"] = executive
  decision["trade_setup"] = trade
  return decision
