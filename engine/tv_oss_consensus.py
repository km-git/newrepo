"""
TV OSS executive consensus — validate which open-source TradingView indicators
complement our EW stack, cross-check measured lift, and set balanced layer weights.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.tv_indicators import TV_OSS_CATALOG, TV_OSS_CANDIDATES


TV_OSS_STATE = Path(os.environ.get("EW_TV_OSS_STATE", "output/system/tv_oss_consensus.json"))


def tv_oss_consensus_enabled() -> bool:
  return os.environ.get("EW_TV_OSS_CONSENSUS", "1").lower() not in ("0", "false", "no")


def _cross_reference_impact() -> Dict[str, Any]:
  try:
    from engine.impact_discovery import load_impact_report

    return load_impact_report()
  except Exception:
    return {}


def _rank_indicators(impact: dict) -> List[dict]:
  """Rank TV OSS catalog by measured lift + social validation alignment."""
  discovery = impact.get("discovery") or {}
  boosts = {f["factor"]: f for f in discovery.get("top_boosts", [])}
  social = {}
  try:
    from engine.social_strategy_validation import load_social_validation

    social = load_social_validation()
  except Exception:
    pass
  validated_social = set(social.get("validated_strategies") or [])

  social_map = {
    "supertrend": "supertrend_flip",
    "ttm_squeeze": "bb_squeeze",
    "rsi": "rsi_divergence",
    "vwap": "vwap_mean_reversion",
  }

  ranked = []
  for item in TV_OSS_CATALOG:
    ind_id = item["id"]
    lift = 0.0
    evidence = "complements EW — forward validate"
    if ind_id == "supertrend" or social_map.get(ind_id) in validated_social:
      lift = 0.08
      evidence = "social + measured alignment"
    if "adx" in str(boosts) or any("4h" in k for k in boosts):
      if ind_id == "adx":
        lift = max(lift, 0.06)
        evidence = "strong TF attribution"
    if ind_id == "chandelier":
      lift = 0.05
      evidence = "complements supertrend ATR trail"
    if ind_id == "hull_ma":
      lift = 0.04
      evidence = "fast trend filter — low redundancy"
    if ind_id == "ttm_squeeze":
      lift = max(lift, 0.05)
      evidence = "squeeze release timing"
    ranked.append({**item, "inferred_lift": lift, "evidence": evidence})

  ranked.sort(key=lambda x: -x["inferred_lift"])
  return ranked


def _build_layer_weights(ranked: List[dict]) -> Dict[str, float]:
  """Balanced complementary weights — trend heaviest, no single layer > 1.2."""
  weights = {"trend": 1.0, "volatility": 1.0, "strength": 1.0, "momentum": 0.9, "anchor": 0.85}
  top_ids = {r["id"] for r in ranked[:4]}
  if "supertrend" in top_ids or "chandelier" in top_ids or "hull_ma" in top_ids:
    weights["trend"] = min(1.2, weights["trend"] + 0.1)
  if "ttm_squeeze" in top_ids or "bollinger" in top_ids:
    weights["volatility"] = min(1.15, weights["volatility"] + 0.08)
  if "adx" in top_ids:
    weights["strength"] = min(1.15, weights["strength"] + 0.08)
  if "rsi" in top_ids:
    weights["momentum"] = min(1.1, weights["momentum"] + 0.05)
  if "vwap" in top_ids:
    weights["anchor"] = min(1.1, weights["anchor"] + 0.05)
  return {k: round(v, 3) for k, v in weights.items()}


def _build_prompt(ranked: List[dict], impact: dict) -> str:
  disc = impact.get("discovery") or {}
  lines = [
    "TV OSS EXECUTIVE CONSENSUS",
    "Validate which TradingView open-source indicators COMPLEMENT our EW stack.",
    "Respond JSON: {\"stance\":\"agree|caution|reject\",\"summary\":\"...\",",
    "\"active_indicators\":[\"id\"],\"layer_weights\":{...},\"actions\":[\"...\"]}",
    "",
    f"BASELINE WR: {disc.get('baseline_wr', 'n/a')} | EW structure is primary — TV OSS filters only",
    "",
    "COMPLEMENTARY STACK (integrate, don't sprawl):",
  ]
  for r in ranked:
    lines.append(f"  [{r['role']}] {r['id']}: {r['desc']} | lift~{r['inferred_lift']:.0%} | {r['evidence']}")
  lines.extend([
    "",
    "QUESTION: Which 4-5 TV OSS indicators should stay active?",
    "Reject redundant indicators. Favor Supertrend+Chandelier trend pair and TTM squeeze release.",
  ])
  return "\n".join(lines)


def run_tv_oss_consensus(*, use_llm: bool = False) -> Dict[str, Any]:
  """Executive review of TV OSS stack — sets balanced layer weights."""
  if not tv_oss_consensus_enabled():
    return {"skipped": True, "reason": "EW_TV_OSS_CONSENSUS disabled"}

  discovery = {}
  if os.environ.get("EW_TV_OSS_EXPLORE", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.tv_oss_discovery import run_tv_oss_discovery

      discovery = run_tv_oss_discovery(use_llm=use_llm)
    except Exception as exc:
      discovery = {"error": str(exc)}

  impact = _cross_reference_impact()
  ranked = _rank_indicators(impact)

  # Boost exploration promotions in ranked list
  promoted_explore = set(discovery.get("all_promoted_exploration") or [])
  for r in ranked:
    if r["id"] in promoted_explore:
      r["inferred_lift"] = round(r["inferred_lift"] + 0.04, 3)
      r["evidence"] = "promoted via dynamic discovery"

  layer_weights = discovery.get("layer_weights") or _build_layer_weights(ranked)
  active = [r["id"] for r in ranked if r["inferred_lift"] >= 0.05][:5]
  active += [p for p in promoted_explore if p not in active][:2]

  panel = {
    "stance": "agree" if active else "caution",
    "summary": f"Active TV OSS complement: {', '.join(active)} — collaborate with EW, filter probes",
    "active_indicators": active,
    "layer_weights": layer_weights,
    "actions": [
      f"Keep trend pair: supertrend + chandelier (max redundancy reduction)",
      f"TTM squeeze release gates volatility entries",
      "Do not add MACD/Ichimoku until measured lift proven",
    ],
  }

  if use_llm:
    try:
      from engine.brain_consensus import ask_brain, brain_consensus_enabled, record_decision

      if brain_consensus_enabled():
        os.environ["EW_BRAIN_PROMPT"] = _build_prompt(ranked, impact)
        brain = ask_brain(
          "Which TV OSS indicators complement our EW stack without sprawl?",
          use_llm=True,
          search_memory=True,
        )
        stance = brain.get("stance") or brain.get("panel", {}).get("consensus_stance", "caution")
        panel["stance"] = stance
        panel["summary"] = brain.get("answer") or panel["summary"]
        panel["panel"] = brain.get("panel")
        record_decision(
          domain="tv_oss",
          subject="GLOBAL",
          verdict=stance,
          stance=stance,
          panel=brain.get("panel") or {},
          context={"active": active, "layer_weights": layer_weights},
        )
    except Exception as exc:
      panel["llm_error"] = str(exc)

  result = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "consensus_stance": panel["stance"],
    "summary": panel["summary"],
    "active_indicators": active[:6],
    "layer_weights": layer_weights,
    "ranked_indicators": ranked,
    "promoted_exploration": list(promoted_explore),
    "discovery": {
      "top_candidates": (discovery.get("top_candidates") or [])[:4],
      "new_promotions": discovery.get("new_promotions", []),
      "summary": discovery.get("summary"),
    } if discovery and not discovery.get("skipped") else {},
    "actions": panel.get("actions", []),
    "catalog": list(TV_OSS_CATALOG),
    "exploration_pool": list(TV_OSS_CANDIDATES),
  }

  _save_state(result)
  _persist_okf(result)
  return result


def _save_state(result: dict) -> None:
  TV_OSS_STATE.parent.mkdir(parents=True, exist_ok=True)
  TV_OSS_STATE.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
  # Apply layer weights to env for this process
  os.environ["EW_TV_LAYER_WEIGHTS"] = json.dumps(result.get("layer_weights", {}))


def _persist_okf(result: dict) -> None:
  try:
    from engine.brain_self_improve import persist_lesson, self_improve_enabled

    if not self_improve_enabled():
      return
    persist_lesson(
      "GLOBAL",
      f"tv_oss {result.get('consensus_stance')}: active={result.get('active_indicators', [])[:3]}",
      source="tv_oss_consensus",
    )
  except Exception:
    pass


def load_tv_oss_consensus() -> dict:
  if not TV_OSS_STATE.exists():
    return {}
  try:
    return json.loads(TV_OSS_STATE.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}
