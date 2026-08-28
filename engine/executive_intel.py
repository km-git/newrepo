"""Executive intel — fuse free data sources + TV OSS into decision scoring."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple


def executive_intel_enabled() -> bool:
  return os.environ.get("EW_EXECUTIVE_INTEL", "1").lower() not in ("0", "false", "no")


def _norm_dir(direction: str) -> str:
  d = str(direction or "").upper()
  if d in ("BULL", "LONG"):
    return "LONG"
  if d in ("BEAR", "SHORT"):
    return "SHORT"
  return d


def load_global_intel() -> Dict[str, Any]:
  """Cached global state: risk consensus, TV OSS stack, impact, deep research."""
  out: Dict[str, Any] = {}
  if not executive_intel_enabled():
    return out

  try:
    from engine.risk_consensus import load_risk_consensus

    out["risk"] = load_risk_consensus()
  except Exception:
    out["risk"] = {}

  try:
    from engine.tv_oss_consensus import load_tv_oss_consensus

    out["tv_oss"] = load_tv_oss_consensus()
  except Exception:
    out["tv_oss"] = {}

  try:
    from engine.impact_discovery import load_impact_report

    out["impact"] = load_impact_report()
  except Exception:
    out["impact"] = {}

  try:
    from engine.deep_research import load_deep_research

    out["deep_research"] = load_deep_research()
  except Exception:
    out["deep_research"] = {}

  try:
    from engine.ai_improvement import load_ai_improvement_state

    out["ai_improvement"] = load_ai_improvement_state()
  except Exception:
    out["ai_improvement"] = {}

  return out


def global_risk_adjustment(intel: Optional[dict] = None) -> float:
  """Risk sizing multiplier delta from global consensus (-0.15 … +0.05)."""
  intel = intel or load_global_intel()
  risk = intel.get("risk") or {}
  try:
    return float(risk.get("risk_adjustment") or 0)
  except (TypeError, ValueError):
    return 0.0


def active_tv_indicators(intel: Optional[dict] = None) -> List[str]:
  intel = intel or load_global_intel()
  tv = intel.get("tv_oss") or {}
  return list(tv.get("active_indicators") or [])


def setup_intel_boost(
  *,
  setup: dict,
  symbol: str = "",
  direction: str = "",
  market_tools: Optional[dict] = None,
  intel: Optional[dict] = None,
) -> Tuple[int, List[str]]:
  """
  Score delta (±25) and tags from TV OSS, free data, global risk posture.
  Uses per-setup indicators + symbol-level market_tools + cached global intel.
  """
  if not executive_intel_enabled():
    return 0, []

  intel = intel or load_global_intel()
  tags: List[str] = []
  delta = 0
  direction = _norm_dir(direction or setup.get("direction", ""))

  # --- TV OSS per-setup ---
  indicators = setup.get("indicators") or {}
  tv_score = indicators.get("tv_score")
  if tv_score is None and market_tools:
    tv_c = (market_tools.get("tv_confluence") or {})
    tv_score = tv_c.get("score")
  if tv_score is not None:
    try:
      ts = int(tv_score)
      if ts >= 70:
        delta += 12
        tags.append(f"tv_oss_strong_{ts}")
      elif ts >= 55:
        delta += 6
        tags.append(f"tv_oss_ok_{ts}")
      elif ts < 45:
        delta -= 8
        tags.append(f"tv_oss_weak_{ts}")
    except (TypeError, ValueError):
      pass

  if indicators.get("tv_aligned") or (market_tools or {}).get("tv_confluence", {}).get("aligned"):
    delta += 5
    tags.append("tv_aligned")

  active = set(active_tv_indicators(intel))
  if active:
    tags.append(f"tv_stack={','.join(sorted(active)[:4])}")

  # --- Free data: fear/greed, WS, social (from market_tools / deep research) ---
  mkt = market_tools or {}
  fg = None
  if mkt.get("web_intel"):
    fg = (mkt["web_intel"].get("fear_greed") or {})
  if not fg:
    dr = intel.get("deep_research") or {}
    fg = ((dr.get("intel") or {}).get("macro") or {}).get("fear_greed") or {}

  if fg and fg.get("available"):
    val = int(fg.get("value") or 50)
    bias = str(fg.get("bias") or "")
    if direction == "LONG" and val <= 25:
      delta += 8
      tags.append(f"fg_extreme_fear_{val}")
    elif direction == "SHORT" and val >= 75:
      delta += 8
      tags.append(f"fg_extreme_greed_{val}")
    elif direction == "LONG" and val >= 80:
      delta -= 6
      tags.append(f"fg_euphoria_{val}")
    elif bias:
      tags.append(f"fg_{bias}")

  ws = mkt.get("ws") or {}
  imb = ws.get("imbalance")
  if imb is not None:
    try:
      imb_f = float(imb)
      if direction == "LONG" and imb_f > 0.15:
        delta += 5
        tags.append(f"ws_bid_imb_{imb_f:+.2f}")
      elif direction == "SHORT" and imb_f < -0.15:
        delta += 5
        tags.append(f"ws_ask_imb_{imb_f:+.2f}")
      elif direction == "LONG" and imb_f < -0.2:
        delta -= 5
        tags.append(f"ws_against_long_{imb_f:+.2f}")
      elif direction == "SHORT" and imb_f > 0.2:
        delta -= 5
        tags.append(f"ws_against_short_{imb_f:+.2f}")
    except (TypeError, ValueError):
      pass

  social = (mkt.get("web_intel") or {}).get("social") or {}
  if social.get("available") and social.get("signals"):
    delta += 3
    tags.append("social_signals")

  boost = mkt.get("confluence_boost", 0)
  if boost:
    delta += min(8, int(boost) // 2)
    for sig in (mkt.get("confluence_signals") or [])[:2]:
      tags.append(sig[:40])

  # --- Global risk consensus ---
  risk = intel.get("risk") or {}
  stance = str(risk.get("consensus_stance") or "")
  if stance == "reject":
    delta -= 12
    tags.append("global_risk_reject")
  elif stance == "caution":
    delta -= 4
    tags.append("global_risk_caution")
  elif stance == "agree":
    delta += 4
    tags.append("global_risk_agree")

  ai = intel.get("ai_improvement") or {}
  ai_stance = str(ai.get("consensus_stance") or "")
  if ai_stance == "reject":
    delta -= 6
    tags.append("ai_improvement_reject")
  elif ai_stance == "agree":
    delta += 3
    tags.append("ai_improvement_agree")

  # --- Impact discovery high-lift factors ---
  impact = intel.get("impact") or {}
  boosts = (impact.get("discovery") or {}).get("top_boosts") or []
  setup_factors = set()
  struct = str(setup.get("wave_structure") or "")
  tf = str(setup.get("timeframe") or "")
  for b in boosts[:5]:
    factor = str(b.get("factor") or "")
    if factor in setup_factors or (
      factor.startswith("tf:") and tf and factor.endswith(tf)
    ) or (
      factor.startswith("wave:") and struct and factor.split(":", 1)[-1] in struct
    ):
      lift = float(b.get("lift_vs_baseline") or 0)
      if lift > 0.1:
        delta += 6
        tags.append(f"impact_{factor}")

  return max(-25, min(25, delta)), tags


def intel_overlay_for_row(row: dict, intel_state: Optional[dict] = None) -> Dict[str, Any]:
  """Live + cached intel for execution consensus on one export row."""
  symbol = row.get("symbol", "")
  direction = _norm_dir(row.get("direction", ""))
  notes: List[str] = []
  stance_hint = "neutral"

  try:
    from gateway.data_hub import live_market_state

    live = live_market_state(symbol, start_ws=os.environ.get("EW_WS_ENABLED", "0") == "1")
  except Exception as exc:
    live = {"error": str(exc)}

  global_intel = intel_state or load_global_intel()
  boost, tags = setup_intel_boost(
    setup={"direction": direction, "timeframe": row.get("timeframe")},
    symbol=symbol,
    direction=direction,
    market_tools=live,
    intel=global_intel,
  )

  if boost >= 8:
    stance_hint = "agree"
    notes.append(f"intel_boost +{boost}")
  elif boost <= -8:
    stance_hint = "caution"
    notes.append(f"intel_drag {boost}")

  fg = ((live.get("web_intel") or {}).get("fear_greed") or {})
  if fg.get("available"):
    val = int(fg.get("value") or 50)
    if direction == "LONG" and val >= 85:
      stance_hint = "caution"
      notes.append(f"extreme_greed_{val}")
    if direction == "SHORT" and val <= 15:
      stance_hint = "caution"
      notes.append(f"extreme_fear_{val}")

  ws_imb = (live.get("ws") or {}).get("imbalance")
  if ws_imb is not None:
    try:
      imb = float(ws_imb)
      if abs(imb) > 0.2:
        against = (direction == "LONG" and imb < -0.2) or (direction == "SHORT" and imb > 0.2)
        if against:
          stance_hint = "caution"
          notes.append(f"ws_against_{imb:+.2f}")
    except (TypeError, ValueError):
      pass

  tv_active = active_tv_indicators(global_intel)
  return {
    "boost": boost,
    "tags": tags,
    "stance_hint": stance_hint,
    "notes": notes,
    "live": live,
    "tv_active": tv_active,
    "global_risk_adj": global_risk_adjustment(global_intel),
  }
