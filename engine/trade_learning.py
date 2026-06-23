"""Learn from failed paper trades — indicators, risk tuning, hedge when SL is broad."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from core.atr import compute_atr14
from core.indicators import compute_raw_indicators, score_indicator_confluence
from engine.outcomes import STYLE_CONFIG

LESSONS_PATH = Path("output/autodream/loss_lessons.json")
LEARNING_STATE_PATH = Path("output/autodream/learning_state.json")
PAPER_LEDGER_DEFAULT = Path("output/autodream/paper_ledger.jsonl")

from core.risk import MAX_STOP_PCT
HEDGE_TRIGGER_MULT = 1.75  # hedge when stop > mult × style max
FAST_STOP_BARS = 3
LEDGER_LOOKBACK = 3000


def _load_ledger(path: Path = PAPER_LEDGER_DEFAULT, limit: int = LEDGER_LOOKBACK) -> List[dict]:
  if not path.exists():
    return []
  rows = []
  with path.open() as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      try:
        rows.append(json.loads(line))
      except json.JSONDecodeError:
        continue
  return rows[-limit:]


def _stop_dist_pct(entry: float, stop: float) -> float:
  if not entry:
    return 0.0
  return abs(entry - stop) / entry * 100


def classify_loss(trade: dict) -> dict:
  """Tag a losing paper trade with failure mode and root cause."""
  style = trade.get("style", "swing")
  entry = float(trade.get("entry") or 0)
  stop = float(trade.get("stop") or 0)
  stop_pct = _stop_dist_pct(entry, stop)
  max_stop = MAX_STOP_PCT.get(style, 4.0)
  bars = int(trade.get("bars_held") or 99)
  readiness = int(trade.get("readiness_score") or 0)
  tier = trade.get("execution_tier", "none")
  exit_detail = trade.get("exit_detail", "")

  modes: List[str] = []
  if stop_pct > max_stop * HEDGE_TRIGGER_MULT:
    modes.append("stop_too_broad")
  elif stop_pct > max_stop:
    modes.append("stop_wide")
  if bars <= FAST_STOP_BARS and "stop" in exit_detail:
    modes.append("fast_stop_hit")
  if tier == "probe":
    modes.append("probe_unconfirmed")
  if readiness < 58:
    modes.append("weak_indicators")
  reason = str(trade.get("honest_reason", ""))
  if "invalid_impulse" in reason or "invalid" in reason.lower():
    modes.append("structure_gap")
  if not modes:
    modes.append("directional_miss")

  return {
    "symbol": trade.get("symbol"),
    "style": style,
    "direction": trade.get("direction"),
    "modes": modes,
    "stop_dist_pct": round(stop_pct, 2),
    "bars_held": bars,
    "readiness_score": readiness,
    "execution_tier": tier,
    "raw_pnl_r": trade.get("raw_pnl_r"),
  }


def analyze_failures(ledger: Optional[List[dict]] = None) -> dict:
  """Aggregate failure patterns from paper ledger losses."""
  ledger = ledger if ledger is not None else _load_ledger()
  losses = [t for t in ledger if t.get("paper_outcome") == "loss"]
  if not losses:
    return {"available": False, "losses": 0, "reason": "no losses in ledger"}

  classified = [classify_loss(t) for t in losses]
  mode_ct = Counter(m for c in classified for m in c["modes"])
  by_style: Dict[str, dict] = defaultdict(lambda: {"losses": 0, "modes": Counter()})
  by_symbol: Dict[str, int] = Counter()
  broad_sl = 0

  for c in classified:
    by_style[c["style"]]["losses"] += 1
    by_style[c["style"]]["modes"].update(c["modes"])
    by_symbol[c["symbol"]] += 1
    if "stop_too_broad" in c["modes"] or "stop_wide" in c["modes"]:
      broad_sl += 1

  lessons: List[str] = []
  if mode_ct.get("stop_too_broad", 0) >= 2:
    lessons.append(
      f"{mode_ct['stop_too_broad']} losses from stops >{HEDGE_TRIGGER_MULT}× style max — use hedge or tighten to structure"
    )
  if mode_ct.get("fast_stop_hit", 0) >= 3:
    lessons.append("Fast stop-outs — wait for zone rejection wick or raise indicator threshold +8")
  if mode_ct.get("weak_indicators", 0) >= 3:
    lessons.append("Losses cluster when readiness <58 — require MACD+EMA alignment before probe")
  if mode_ct.get("probe_unconfirmed", 0) >= 3:
    lessons.append("Probe losses without impulse — cut probe size to 25% until EW validates")
  if mode_ct.get("structure_gap", 0) >= 2:
    lessons.append("Invalid impulse losses — do not probe until R1/R2/R3 pass on style TF")

  worst_style = max(by_style.items(), key=lambda x: x[1]["losses"], default=(None, {}))
  if worst_style[0] and worst_style[1]["losses"] >= 3:
    lessons.append(f"Style hotspot: {worst_style[0]} ({worst_style[1]['losses']} recent losses)")

  return {
    "available": True,
    "updated": datetime.now(timezone.utc).isoformat(),
    "losses_analyzed": len(losses),
    "mode_counts": dict(mode_ct),
    "broad_stop_losses": broad_sl,
    "by_style": {
      k: {"losses": v["losses"], "top_modes": dict(v["modes"].most_common(3))}
      for k, v in by_style.items()
    },
    "by_symbol": dict(by_symbol.most_common(10)),
    "lessons": lessons,
    "classified": classified[-50:],
  }


def build_hedge_plan(setup: dict, symbol: str) -> Optional[dict]:
  """
  When stop is too broad, recommend partial hedge instead of full directional risk.
  """
  style = setup.get("style", "swing")
  entry = float(setup.get("entry", {}).get("anchor") or 0)
  stop = float(setup.get("stop_loss", {}).get("price") or 0)
  if not entry or not stop:
    return None

  stop_pct = setup.get("stop_loss", {}).get("distance_pct")
  if stop_pct is None:
    stop_pct = _stop_dist_pct(entry, stop)
  max_stop = MAX_STOP_PCT.get(style, 4.0)
  direction = setup.get("direction", "LONG")

  if float(stop_pct) <= max_stop * HEDGE_TRIGGER_MULT:
    return None

  hedge_dir = "SHORT" if direction == "LONG" else "LONG"
  hedge_sym = "BTC/USDT" if "BTC" not in symbol.upper() else "ETH/USDT"
  ratio = 0.35 if float(stop_pct) > max_stop * 2.5 else 0.25

  return {
    "required": True,
    "reason": f"SL {float(stop_pct):.1f}% exceeds {max_stop * HEDGE_TRIGGER_MULT:.1f}% cap for {style}",
    "action": "partial_delta_hedge",
    "hedge_direction": hedge_dir,
    "hedge_instrument": hedge_sym,
    "hedge_size_pct": int(ratio * 100),
    "primary_size_pct": int((1 - ratio) * 100),
    "alt_tighten": f"Cap SL at {max_stop:.1f}% via structure+0.7×ATR",
    "alt_skip": "Skip until impulse valid and SL inside cap",
  }


def suggest_risk_adjustments(
  setup: dict,
  df: Optional[pd.DataFrame],
  learning: dict,
  symbol: str,
) -> dict:
  """Fine-tune sizing, stops, and indicator gates from loss patterns."""
  style = setup.get("style", "swing")
  cfg = STYLE_CONFIG.get(style, STYLE_CONFIG["swing"])
  adjustments: List[str] = []
  size_mult = 1.0
  ind_boost = 0
  tighten_stop_pct: Optional[float] = None

  entry = float(setup.get("entry", {}).get("anchor") or 0)
  stop = float(setup.get("stop_loss", {}).get("price") or 0)
  stop_pct = float(setup.get("stop_loss", {}).get("distance_pct") or _stop_dist_pct(entry, stop))
  max_stop = MAX_STOP_PCT.get(style, 4.0)

  sym_losses = learning.get("by_symbol", {}).get(symbol, 0)
  style_block = (learning.get("by_style") or {}).get(style, {})
  style_losses = style_block.get("losses", 0)
  modes = learning.get("mode_counts", {})

  if stop_pct > max_stop:
    tighten_stop_pct = max_stop
    adjustments.append(f"tighten SL cap to {max_stop}% (was {stop_pct:.1f}%)")

  if stop_pct > max_stop * HEDGE_TRIGGER_MULT:
    adjustments.append("broad SL — hedge or skip (see hedge_plan)")

  if sym_losses >= 2:
    size_mult *= 0.7
    adjustments.append(f"symbol {sym_losses} recent losses — size ×0.7")

  if style_losses >= 5:
    ind_boost += 8
    adjustments.append(f"{style} loss cluster — indicator threshold +8")

  if modes.get("fast_stop_hit", 0) >= 3:
    ind_boost += 5
    adjustments.append("fast stop pattern — require zone rejection wick")

  if modes.get("probe_unconfirmed", 0) >= 3 and setup.get("execution_tier") == "probe":
    size_mult *= 0.5
    adjustments.append("probe losses — cut to 25% max until EW validates")

  if modes.get("weak_indicators", 0) >= 3 and df is not None and len(df) >= 20:
    zone = setup.get("entry", {}).get("zone") or [entry, entry]
    ind = score_indicator_confluence(
      df, setup.get("direction", "LONG"), zone[0], zone[1], style
    )
    if ind["score"] < ind.get("threshold", 58) + ind_boost:
      adjustments.append(
        f"indicators {ind['score']}/{ind.get('threshold', 58) + ind_boost} below loss-adjusted gate"
      )

  # Live indicator fine-tune on current bar
  if df is not None and len(df) >= 20:
    raw = compute_raw_indicators(df)
    direction = setup.get("direction", "LONG")
    is_long = direction == "LONG"
    if is_long and not raw["above_ema20"] and modes.get("directional_miss", 0) >= 2:
      ind_boost += 5
      adjustments.append("LONG losses below EMA20 — require reclaim before entry")
    if not is_long and raw["above_ema20"] and modes.get("directional_miss", 0) >= 2:
      ind_boost += 5
      adjustments.append("SHORT losses above EMA20 — require rejection before entry")

  account_risk = setup.get("risk", {}).get("account_risk_pct", cfg["account_risk_pct"])
  adjusted_risk = round(float(account_risk) * size_mult, 3)

  return {
    "size_multiplier": round(size_mult, 2),
    "indicator_threshold_boost": ind_boost,
    "tighten_stop_max_pct": tighten_stop_pct,
    "adjusted_account_risk_pct": adjusted_risk,
    "adjustments": adjustments,
  }


def apply_tighter_stop(setup: dict, max_stop_pct: float) -> dict:
  """Cap stop distance when learning flags broad SL."""
  entry = float(setup.get("entry", {}).get("anchor") or 0)
  stop = float(setup.get("stop_loss", {}).get("price") or 0)
  direction = setup.get("direction", "LONG")
  if not entry or not stop or not max_stop_pct:
    return setup

  current_pct = _stop_dist_pct(entry, stop)
  if current_pct <= max_stop_pct:
    return setup

  risk = entry * max_stop_pct / 100
  new_stop = entry - risk if direction == "LONG" else entry + risk
  setup = dict(setup)
  sl = dict(setup.get("stop_loss") or {})
  sl["price"] = round(new_stop, 6)
  sl["distance_pct"] = round(max_stop_pct, 2)
  sl["rule"] = (sl.get("rule", "") + f" · autodream capped at {max_stop_pct}%").strip()
  setup["stop_loss"] = sl
  setup["risk_adjusted_stop"] = True
  return setup


def apply_learning_to_setup(
  setup: dict,
  symbol: str,
  df: Optional[pd.DataFrame],
  learning: dict,
) -> dict:
  """Merge loss lessons, risk tweaks, and hedge plan into one setup."""
  if not setup or setup.get("status") == "not_actionable":
    return setup

  setup = dict(setup)
  risk_adj = suggest_risk_adjustments(setup, df, learning, symbol)
  hedge = build_hedge_plan(setup, symbol)

  if risk_adj.get("tighten_stop_max_pct"):
    setup = apply_tighter_stop(setup, float(risk_adj["tighten_stop_max_pct"]))

  if risk_adj.get("size_multiplier", 1.0) < 1.0 and setup.get("risk"):
    risk = dict(setup["risk"])
    risk_base = float(risk_adj.get("adjusted_account_risk_pct") or risk.get("account_risk_pct", 1))
    risk["account_risk_pct"] = risk_base
    risk["sizing_rule"] = (
      risk.get("sizing_rule", "")
      + f" · loss-learning size ×{risk_adj['size_multiplier']}"
    ).strip()
    setup["risk"] = risk

  if hedge:
    setup["hedge_plan"] = hedge
    if setup.get("execution_tier") == "probe":
      setup["honest_reason"] = (
        setup.get("honest_reason", "")
        + f" · HEDGE: {hedge['hedge_size_pct']}% {hedge['hedge_direction']} {hedge['hedge_instrument']} (broad SL)"
      )

  lessons = list(learning.get("lessons", [])[:2])
  if risk_adj.get("adjustments"):
    lessons.extend(risk_adj["adjustments"][:2])

  setup["loss_learning"] = {
    "risk_adjustment": risk_adj,
    "hedge_plan": hedge,
    "lessons": lessons,
  }
  if lessons:
    setup["loss_lesson"] = "; ".join(lessons[:3])
  if risk_adj.get("indicator_threshold_boost"):
    setup["readiness_gate_boost"] = risk_adj["indicator_threshold_boost"]

  return setup


def apply_learning_to_outcomes(
  outcomes: dict,
  symbol: str,
  data: dict,
  learning: Optional[dict] = None,
) -> dict:
  """Apply loss learning across all styles for one symbol."""
  learning = learning or analyze_failures()
  if not learning.get("available"):
    return outcomes

  style_tf = {"scalp": "15m", "day_trade": "1h", "swing": "1d", "long_term": "1w"}
  for style, setup in outcomes.get("setups", {}).items():
    tf = style_tf.get(style, "1d")
    df = data.get(tf)
    if df is not None and hasattr(df, "__len__") and len(df) == 0:
      df = None
    outcomes["setups"][style] = apply_learning_to_setup(
      setup, symbol, df, learning
    )

  outcomes.setdefault("autodream", {})["loss_learning"] = {
    "losses_analyzed": learning.get("losses_analyzed"),
    "lessons": learning.get("lessons", [])[:5],
    "mode_counts": learning.get("mode_counts"),
  }
  return outcomes


def save_learning_state(learning: dict, path: Path = LEARNING_STATE_PATH) -> str:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(learning, indent=2, default=str))
  return str(path)


def save_loss_lessons(learning: dict, path: Path = LESSONS_PATH) -> str:
  path.parent.mkdir(parents=True, exist_ok=True)
  doc = {k: v for k, v in learning.items() if k != "classified"}
  path.write_text(json.dumps(doc, indent=2, default=str))
  return str(path)


def run_loss_learning_cycle() -> dict:
  """Analyze ledger failures and persist lessons for next pipeline run."""
  learning = analyze_failures()
  if learning.get("available"):
    save_learning_state(learning)
    save_loss_lessons(learning)
  return learning
