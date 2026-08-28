"""Executive intel — fuse free data, TV OSS, market structure into decision scoring."""

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
  out: Dict[str, Any] = {}
  if not executive_intel_enabled():
    return out
  for key, mod_path, fn in (
    ("risk", "engine.risk_consensus", "load_risk_consensus"),
    ("tv_oss", "engine.tv_oss_consensus", "load_tv_oss_consensus"),
    ("impact", "engine.impact_discovery", "load_impact_report"),
    ("deep_research", "engine.deep_research", "load_deep_research"),
    ("ai_improvement", "engine.ai_improvement", "load_ai_improvement_state"),
    ("gap_audit", "engine.resource_gap_audit", "load_gap_audit"),
  ):
    try:
      mod = __import__(mod_path, fromlist=[fn])
      out[key] = getattr(mod, fn)()
    except Exception:
      out[key] = {}
  return out


def global_risk_adjustment(intel: Optional[dict] = None) -> float:
  intel = intel or load_global_intel()
  try:
    return float((intel.get("risk") or {}).get("risk_adjustment") or 0)
  except (TypeError, ValueError):
    return 0.0


def active_tv_indicators(intel: Optional[dict] = None) -> List[str]:
  intel = intel or load_global_intel()
  return list((intel.get("tv_oss") or {}).get("active_indicators") or [])


def setup_intel_boost(
  *,
  setup: dict,
  symbol: str = "",
  direction: str = "",
  market_tools: Optional[dict] = None,
  intel: Optional[dict] = None,
) -> Tuple[int, List[str]]:
  if not executive_intel_enabled():
    return 0, []

  intel = intel or load_global_intel()
  tags: List[str] = []
  delta = 0
  direction = _norm_dir(direction or setup.get("direction", ""))
  mkt = market_tools or {}

  indicators = setup.get("indicators") or {}
  tv_score = indicators.get("tv_score")
  if tv_score is None:
    tv_score = (mkt.get("tv_confluence") or {}).get("score")
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

  if indicators.get("tv_aligned") or (mkt.get("tv_confluence") or {}).get("aligned"):
    delta += 5
    tags.append("tv_aligned")

  ms = mkt.get("market_structure") or {}
  if ms.get("available"):
    ms_score = (mkt.get("ms_structure") or {}).get("score", 50)
    if ms.get("aligned") or (mkt.get("ms_structure") or {}).get("aligned"):
      delta += 8
      tags.append(f"structure_{ms.get('event', 'ok')}")
    elif ms_score < 42:
      delta -= 6
      tags.append("structure_against")

  fg = (mkt.get("web_intel") or {}).get("fear_greed") or {}
  if not fg.get("available"):
    fg = ((intel.get("deep_research") or {}).get("intel") or {}).get("macro", {}).get("fear_greed") or {}
  if fg.get("available"):
    val = int(fg.get("value") or 50)
    if direction == "LONG" and val <= 25:
      delta += 8
      tags.append(f"fg_extreme_fear_{val}")
    elif direction == "SHORT" and val >= 75:
      delta += 8
      tags.append(f"fg_extreme_greed_{val}")
    elif direction == "LONG" and val >= 80:
      delta -= 6
      tags.append(f"fg_euphoria_{val}")

  oi = (mkt.get("web_intel") or {}).get("open_interest") or {}
  if oi.get("available") and oi.get("open_interest"):
    delta += 2
    tags.append("oi_available")

  ws = mkt.get("live_ws") or mkt.get("ws") or {}
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
    except (TypeError, ValueError):
      pass

  boost = mkt.get("confluence_boost", 0)
  if boost:
    delta += min(8, int(boost) // 2)
    for sig in (mkt.get("confluence_signals") or [])[:2]:
      tags.append(str(sig)[:40])

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

  impact = intel.get("impact") or {}
  for b in ((impact.get("discovery") or {}).get("top_boosts") or [])[:5]:
    factor = str(b.get("factor") or "")
    tf = str(setup.get("timeframe") or "")
    if factor.startswith("tf:") and tf and factor.endswith(tf):
      if float(b.get("lift_vs_baseline") or 0) > 0.1:
        delta += 6
        tags.append(f"impact_{factor}")

  return max(-25, min(25, delta)), tags
