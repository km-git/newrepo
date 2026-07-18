"""
TV OSS dynamic discovery — explore new value-driven TradingView open-source
indicators, score regime fit, and fine-tune via multi-AI executive consensus.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from core.tv_indicators import (
  TV_OSS_CANDIDATES,
  TV_OSS_CATALOG,
  compute_exploration_signals,
  score_candidate_alignment,
)


DISCOVERY_STATE = Path(os.environ.get("EW_TV_OSS_DISCOVERY_STATE", "output/system/tv_oss_discovery.json"))


def tv_oss_explore_enabled() -> bool:
  return os.environ.get("EW_TV_OSS_EXPLORE", "1").lower() not in ("0", "false", "no")


def _sample_ohlcv(n: int = 120) -> pd.DataFrame:
  rng = np.random.default_rng(int(datetime.now().timestamp()) % 10000)
  close = 100 * np.cumprod(1 + rng.normal(0.0005, 0.012, n))
  high = close * (1 + rng.uniform(0, 0.01, n))
  low = close * (1 - rng.uniform(0, 0.01, n))
  return pd.DataFrame({
    "Open": close,
    "High": high,
    "Low": low,
    "Close": close,
    "Volume": rng.uniform(1000, 8000, n),
  })


def _load_active_roles() -> set:
  try:
    from engine.tv_oss_consensus import load_tv_oss_consensus

    state = load_tv_oss_consensus()
    active = set(state.get("active_indicators") or [])
    roles = {c["role"] for c in TV_OSS_CATALOG if c["id"] in active}
    return roles
  except Exception:
    return {c["role"] for c in TV_OSS_CATALOG}


def _role_gap_bonus(role: str, active_roles: set) -> float:
  """Reward candidates that fill gaps in the active stack."""
  if role not in active_roles:
    return 0.15
  if role in ("flow",) and role not in active_roles:
    return 0.20
  return 0.0


def _regime_bonus(sig: dict, atr_pct: float) -> float:
  """Dynamic value shifts with volatility regime."""
  signal = sig.get("signal", "neutral")
  if atr_pct > 4 and signal in ("squeeze_on", "neutral"):
    return 0.05
  if atr_pct < 2 and signal in ("accumulation", "distribution", "bullish", "bearish"):
    return 0.03
  return 0.0


def explore_candidates(
  df: Optional[pd.DataFrame] = None,
  *,
  direction: str = "LONG",
) -> List[dict]:
  """
  Score exploration-pool indicators by dynamic value:
  role gap + alignment + regime fit + social heat proxy.
  """
  df = df if df is not None and len(df) >= 50 else _sample_ohlcv()
  exploration = compute_exploration_signals(df)
  active_roles = _load_active_roles()
  atr_pct = 0.0
  try:
    from core.tv_indicators import compute_tv_signals

    atr_pct = (compute_tv_signals(df) or {}).get("atr_pct", 0)
  except Exception:
    pass

  social_heat: Dict[str, float] = {}
  try:
    from engine.social_strategy_validation import load_social_validation

    sv = load_social_validation()
    for c in sv.get("top_candidates") or []:
      if c.get("id"):
        social_heat[c["id"]] = float(c.get("social_heat") or 0)
  except Exception:
    pass

  ranked: List[dict] = []
  for cand in TV_OSS_CANDIDATES:
    ind_id = cand["id"]
    sig = exploration.get(ind_id) or {}
    if not sig.get("available"):
      continue

    align = score_candidate_alignment(ind_id, sig, direction)
    gap = _role_gap_bonus(cand["role"], active_roles)
    regime = _regime_bonus(sig, atr_pct)
    social = min(0.10, social_heat.get(ind_id, 0) / 500)

    # Redundancy penalty vs active stack same role
    redundancy = -0.08 if cand["role"] in active_roles and cand["role"] in ("momentum", "strength") else 0.0

    dynamic_value = round(
      (align / 100) * 0.45 + gap + regime + social + redundancy,
      4,
    )
    priority = "high" if dynamic_value >= 0.55 else "medium" if dynamic_value >= 0.35 else "low"

    ranked.append({
      **cand,
      "alignment_score": align,
      "dynamic_value": dynamic_value,
      "priority": priority,
      "signal": sig.get("signal"),
      "role_gap": gap > 0,
      "regime_bonus": regime,
    })

  ranked.sort(key=lambda x: -x["dynamic_value"])
  return ranked


def _build_finetune_prompt(candidates: List[dict], impact: dict, current_weights: dict) -> str:
  disc = impact.get("discovery") or {}
  lines = [
    "TV OSS DYNAMIC DISCOVERY & FINE-TUNE",
    "Explore new value-driven TradingView open-source indicators.",
    "Respond JSON: {\"stance\":\"agree|caution|reject\",\"summary\":\"...\",",
    "\"promote\":[\"id\"],\"demote\":[\"id\"],\"layer_weights\":{...},\"param_tweaks\":{}}",
    "",
    f"BASELINE WR: {disc.get('baseline_wr')} | Active stack must stay ≤6 indicators",
    f"CURRENT WEIGHTS: {json.dumps(current_weights)}",
    "",
    "EXPLORATION CANDIDATES (ranked by dynamic value):",
  ]
  for c in candidates[:6]:
    lines.append(
      f"  [{c['priority']}] {c['id']} ({c['role']}): value={c['dynamic_value']:.2f} "
      f"align={c['alignment_score']} signal={c.get('signal')} — {c['desc']}"
    )
  lines.extend([
    "",
    "RULES:",
    "- Promote max 1-2 candidates per cycle if dynamic_value ≥ 0.55",
    "- Prefer flow/volume indicators (CMF, OBV) — gap in active stack",
    "- Fine-tune layer_weights ±0.05 max per cycle",
    "- Reject redundant momentum indicators if RSI+Stoch RSI overlap",
    "",
    "QUESTION: Which new TV OSS indicators to promote and how to fine-tune weights?",
  ])
  return "\n".join(lines)


def _rule_finetune(candidates: List[dict], current_weights: dict) -> Dict[str, Any]:
  """Rule-based fine-tune when LLM unavailable."""
  promote = [c["id"] for c in candidates if c["dynamic_value"] >= 0.55 and c["priority"] == "high"][:2]
  weights = dict(current_weights)
  for c in candidates[:3]:
    if c["role"] == "flow" and c["dynamic_value"] >= 0.45:
      weights["flow"] = min(1.1, weights.get("flow", 0.85) + 0.05)
    if c["role"] == "momentum" and c["id"] == "williams_r" and c["dynamic_value"] >= 0.50:
      weights["momentum"] = min(1.15, weights.get("momentum", 0.9) + 0.03)

  return {
    "stance": "agree" if promote else "caution",
    "summary": f"Promote exploration candidates: {promote}" if promote else "No candidate clears dynamic value bar — keep exploring",
    "promote": promote,
    "demote": [],
    "layer_weights": {k: round(v, 3) for k, v in weights.items()},
    "param_tweaks": {},
  }


def fine_tune_with_consensus(
  candidates: List[dict],
  *,
  current_weights: Optional[dict] = None,
  use_llm: bool = False,
) -> Dict[str, Any]:
  """Multi-AI executive fine-tune of TV OSS stack and exploration promotions."""
  current_weights = current_weights or {
    "trend": 1.0, "volatility": 1.0, "strength": 1.0, "momentum": 0.9, "anchor": 0.85, "flow": 0.85,
  }
  impact: dict = {}
  try:
    from engine.impact_discovery import load_impact_report

    impact = load_impact_report()
  except Exception:
    pass

  panel = _rule_finetune(candidates, current_weights)

  if use_llm:
    try:
      from engine.brain_consensus import ask_brain, brain_consensus_enabled, record_decision

      if brain_consensus_enabled():
        os.environ["EW_BRAIN_PROMPT"] = _build_finetune_prompt(candidates, impact, current_weights)
        brain = ask_brain(
          "Fine-tune TV OSS stack: promote high dynamic-value indicators, adjust layer weights?",
          use_llm=True,
          search_memory=True,
        )
        stance = brain.get("stance") or brain.get("panel", {}).get("consensus_stance", "caution")
        panel["stance"] = stance
        panel["summary"] = brain.get("answer") or panel["summary"]
        panel["panel"] = brain.get("panel")
        record_decision(
          domain="tv_oss_discovery",
          subject="GLOBAL",
          verdict=stance,
          stance=stance,
          panel=brain.get("panel") or {},
          context={"promote": panel.get("promote"), "top_candidate": candidates[0]["id"] if candidates else None},
        )
    except Exception as exc:
      panel["llm_error"] = str(exc)

  return panel


def run_tv_oss_discovery(*, use_llm: bool = False, direction: str = "LONG") -> Dict[str, Any]:
  """Full exploration + fine-tune cycle."""
  if not tv_oss_explore_enabled():
    return {"skipped": True, "reason": "EW_TV_OSS_EXPLORE disabled"}

  candidates = explore_candidates(direction=direction)
  current_weights = {}
  promoted_existing: List[str] = []
  try:
    from engine.tv_oss_consensus import load_tv_oss_consensus

    state = load_tv_oss_consensus()
    current_weights = state.get("layer_weights") or {}
    promoted_existing = list(state.get("promoted_exploration") or [])
  except Exception:
    pass

  finetune = fine_tune_with_consensus(candidates, current_weights=current_weights, use_llm=use_llm)
  new_promotions = [p for p in finetune.get("promote", []) if p not in promoted_existing]

  result = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "consensus_stance": finetune.get("stance", "caution"),
    "summary": finetune.get("summary", ""),
    "candidates_explored": len(candidates),
    "top_candidates": candidates[:6],
    "promoted": finetune.get("promote", []),
    "new_promotions": new_promotions,
    "all_promoted_exploration": list(dict.fromkeys(promoted_existing + new_promotions)),
    "layer_weights": finetune.get("layer_weights", current_weights),
    "param_tweaks": finetune.get("param_tweaks", {}),
    "panel": finetune.get("panel"),
  }

  _save_state(result)
  _apply_finetune(result)
  _persist_okf(result)
  return result


def _save_state(result: dict) -> None:
  DISCOVERY_STATE.parent.mkdir(parents=True, exist_ok=True)
  DISCOVERY_STATE.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


def _apply_finetune(result: dict) -> None:
  """Merge discovery fine-tune into consensus state and env."""
  weights = result.get("layer_weights")
  if weights:
    os.environ["EW_TV_LAYER_WEIGHTS"] = json.dumps(weights)
  try:
    from engine.tv_oss_consensus import load_tv_oss_consensus, TV_OSS_STATE

    state = load_tv_oss_consensus()
    if state:
      state["layer_weights"] = weights or state.get("layer_weights")
      state["promoted_exploration"] = result.get("all_promoted_exploration", [])
      state["discovery_summary"] = result.get("summary")
      state["last_discovery_utc"] = result.get("timestamp_utc")
      TV_OSS_STATE.parent.mkdir(parents=True, exist_ok=True)
      TV_OSS_STATE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
  except Exception:
    pass


def _persist_okf(result: dict) -> None:
  try:
    from engine.brain_self_improve import persist_lesson, self_improve_enabled

    if not self_improve_enabled():
      return
    promoted = result.get("promoted", [])[:2]
    persist_lesson(
      "GLOBAL",
      f"tv_oss_discovery {result.get('consensus_stance')}: explore promote={promoted}",
      source="tv_oss_discovery",
    )
  except Exception:
    pass


def load_tv_oss_discovery() -> dict:
  if not DISCOVERY_STATE.exists():
    return {}
  try:
    return json.loads(DISCOVERY_STATE.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}
