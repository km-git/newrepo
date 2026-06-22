"""Expert EW direction resolver — always resolve BULL/BEAR via layered confluence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

TF_STACK = ["1w", "1d", "4h", "1h", "15m"]
TF_WEIGHTS = {"1w": 3.0, "1d": 2.5, "4h": 2.0, "1h": 1.5, "15m": 1.2}


def _vote(direction: str, weight: float, source: str, votes: List[dict]) -> None:
  if direction not in ("BULL", "BEAR"):
    return
  votes.append({"direction": direction, "weight": weight, "source": source})


def _abc_direction(wave: dict) -> Optional[str]:
  abc = wave.get("abc")
  if not abc:
    return None
  struct = wave.get("structure", "")
  if "abc" not in struct:
    return None
  # C-wave in progress: last leg of ABC defines completion direction
  last5 = wave.get("waves_last5") or []
  if last5:
    leg = last5[-1]
    t = leg.get("type", "")
    if t == "Up":
      return "BULL"
    if t == "Down":
      return "BEAR"
  return None


def _last_monowave_direction(adaptive: dict, tf: str) -> Optional[str]:
  ad = adaptive.get(tf, {})
  mws = ad.get("monowaves") or []
  if not mws:
    return None
  last = mws[-1]
  if last.get("type") == "Up":
    return "BULL"
  if last.get("type") == "Down":
    return "BEAR"
  return None


def _htf_bias_direction(htf_class: dict) -> Optional[str]:
  bias = (htf_class or {}).get("bias", "").lower()
  if "bull" in bias or "reversal_up" in bias or "up" in bias:
    return "BULL"
  if "bear" in bias or "reversal_down" in bias or "down" in bias:
    return "BEAR"
  state = (htf_class or {}).get("state", "").lower()
  if "bull" in state:
    return "BULL"
  if "bear" in state:
    return "BEAR"
  return None


def _harmonic_direction(harmonic_overlaps: List[dict]) -> Optional[str]:
  if not harmonic_overlaps:
    return None
  bull = sum(1 for h in harmonic_overlaps if h.get("bullish", True))
  bear = len(harmonic_overlaps) - bull
  if bull > bear:
    return "BULL"
  if bear > bull:
    return "BEAR"
  return None


def build_sentinel_stack(
  wave_structure: dict,
  adaptive: dict,
  htf_class: dict,
  consensus: dict,
  cycle_confluence: dict,
  harmonic_overlaps: List[dict],
  market_tools: Optional[dict] = None,
  sentinel_analysis: Optional[dict] = None,
) -> dict:
  """
  Sentinel-style multi-signal stack — each layer votes with weight.
  Combines EW matrix, Hurst cycles, harmonics, HTF, RSI, consensus.
  """
  votes: List[dict] = []

  # EW matrix per TF
  for tf in TF_STACK:
    w = wave_structure.get(tf, {})
    if not w or w.get("structure") == "no_data":
      continue
    wt = TF_WEIGHTS.get(tf, 1.0)
    if w.get("impulse_valid"):
      _vote(w.get("direction", "NEUTRAL"), wt * 1.5, f"{tf}_impulse_valid", votes)
    elif w.get("direction") in ("BULL", "BEAR"):
      _vote(w["direction"], wt * 0.8, f"{tf}_impulse_partial", votes)
    abc_d = _abc_direction(w)
    if abc_d:
      _vote(abc_d, wt * 1.2, f"{tf}_abc", votes)
    if w.get("diagonal") in ("BULL", "BEAR"):
      _vote(w["diagonal"], wt * 1.0, f"{tf}_diagonal", votes)
    mw_d = _last_monowave_direction(adaptive, tf)
    if mw_d:
      _vote(mw_d, wt * 0.6, f"{tf}_last_leg", votes)

  # HTF classification
  htf_d = _htf_bias_direction(htf_class)
  if htf_d:
    _vote(htf_d, 3.0, "htf_bias", votes)

  # Multi-engine EW consensus
  c_dir = (consensus or {}).get("consensus_direction", "NEUTRAL")
  c_score = (consensus or {}).get("consensus_score", 0)
  if c_dir in ("BULL", "BEAR"):
    _vote(c_dir, 2.5 + c_score, "ew_consensus", votes)

  # Hurst / dominant cycle
  cc = cycle_confluence or {}
  cy_dir = cc.get("cycle_direction", "NEUTRAL")
  cy_conf = cc.get("cycle_confidence", 0)
  if cy_dir in ("BULL", "BEAR"):
    _vote(cy_dir, 2.0 + cy_conf, "hurst_cycle", votes)

  # Harmonics
  h_dir = _harmonic_direction(harmonic_overlaps)
  if h_dir:
    _vote(h_dir, 1.5, "harmonic_prz", votes)

  # RSI stack (sentinel momentum layer)
  mkt = market_tools or {}
  rsi = mkt.get("multi_tf_rsi", {})
  rsi_bias = rsi.get("bias", "NEUTRAL")
  if rsi_bias in ("BULL", "BEAR"):
    _vote(rsi_bias, 1.2, "rsi_stack", votes)

  div = mkt.get("rsi_divergence")
  if div == "bullish_divergence":
    _vote("BULL", 1.8, "rsi_divergence", votes)
  elif div == "bearish_divergence":
    _vote("BEAR", 1.8, "rsi_divergence", votes)

  # Sentinel Trader fusion processor (dedicated adapter)
  sa = sentinel_analysis or {}
  if sa.get("available") and sa.get("direction") in ("BULL", "BEAR"):
    _vote(sa["direction"], 2.8 + sa.get("confidence", 0.5), "sentinel_trader", votes)

  bull = sum(v["weight"] for v in votes if v["direction"] == "BULL")
  bear = sum(v["weight"] for v in votes if v["direction"] == "BEAR")
  total = bull + bear

  if total == 0:
    direction = "BULL"
    confidence = 0.35
    method = "default_bull_tiebreak"
  elif bull >= bear:
    direction = "BULL"
    confidence = round(bull / total, 3) if total else 0.5
    method = "sentinel_weighted"
  else:
    direction = "BEAR"
    confidence = round(bear / total, 3) if total else 0.5
    method = "sentinel_weighted"

  margin = abs(bull - bear) / total if total else 0
  conviction = "high" if confidence >= 0.65 and margin >= 0.2 else "medium" if confidence >= 0.55 else "low"

  top_sources = sorted(votes, key=lambda v: v["weight"], reverse=True)[:5]
  signals = [f"{v['source']}→{v['direction']}({v['weight']:.1f})" for v in top_sources]

  return {
    "direction": direction,
    "confidence": confidence,
    "conviction": conviction,
    "method": method,
    "bull_weight": round(bull, 2),
    "bear_weight": round(bear, 2),
    "margin_pct": round(margin * 100, 1),
    "votes": votes,
    "top_signals": signals,
    "hurst_regime": cc.get("primary_regime"),
    "cycle_phase": cc.get("primary_phase"),
    "cycle_period": cc.get("primary_period"),
    "sentinel_direction": (sentinel_analysis or {}).get("direction"),
    "sentinel_confidence": (sentinel_analysis or {}).get("confidence"),
  }


def resolve_expert_direction(
  wave_structure: dict,
  adaptive: dict,
  htf_class: dict,
  consensus: dict,
  cycle_confluence: dict,
  harmonic_overlaps: List[dict],
  exec_direction: str,
  execution_passes: bool,
  market_tools: Optional[dict] = None,
  sentinel_analysis: Optional[dict] = None,
) -> dict:
  """
  Expert Elliott Wave direction — always BULL or BEAR with confidence + audit trail.
  When strict 15m impulse fails, sentinel + Hurst + EW stack still resolve bias.
  """
  sentinel = build_sentinel_stack(
    wave_structure, adaptive, htf_class, consensus,
    cycle_confluence, harmonic_overlaps, market_tools,
    sentinel_analysis=sentinel_analysis,
  )

  direction = sentinel["direction"]
  confidence = sentinel["confidence"]
  method = sentinel["method"]
  notes: List[str] = list(sentinel.get("top_signals", []))

  # Strict impulse confirmation boosts confidence
  if execution_passes and exec_direction in ("BULL", "BEAR"):
    if exec_direction == direction:
      confidence = min(0.92, confidence + 0.12)
      notes.insert(0, f"15m_impulse_confirms_{exec_direction}")
    else:
      notes.insert(0, f"15m_split: exec={exec_direction} vs expert={direction}")
      confidence = max(0.45, confidence - 0.08)

  # Consensus agreement boost
  c_dir = (consensus or {}).get("consensus_direction")
  if c_dir == direction:
    confidence = min(0.9, confidence + 0.06)

  agreement_count = sum(1 for v in sentinel["votes"] if v["direction"] == direction)
  return {
    "direction": direction,
    "confidence": round(confidence, 3),
    "conviction": sentinel["conviction"],
    "method": method,
    "agreement_votes": agreement_count,
    "total_votes": len(sentinel["votes"]),
    "confluence_signals": notes[:6],
    "hurst_regime": sentinel.get("hurst_regime"),
    "cycle_phase": sentinel.get("cycle_phase"),
    "cycle_period_bars": sentinel.get("cycle_period"),
    "cycle_direction": cycle_confluence.get("cycle_direction"),
    "ehlers_phase_deg": cycle_confluence.get("primary_ehlers_phase"),
    "sentinel_direction": (sentinel_analysis or {}).get("direction"),
    "sentinel_confidence": (sentinel_analysis or {}).get("confidence"),
    "sentinel": sentinel,
    "honest_note": (
      f"Expert {direction} ({confidence:.0%}) via {method}: "
      f"{agreement_count}/{len(sentinel['votes'])} layers agree · "
      f"Hurst {cycle_confluence.get('primary_regime', 'n/a')} · "
      f"phase {sentinel.get('cycle_phase', 'n/a')}"
    ),
  }
