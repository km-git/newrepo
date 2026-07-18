"""
Impact discovery — find hidden high-leverage factors from resolved outcomes.

Mines closed setups to rank what actually moves win rate vs baseline.
Feeds balanced signal weights into dynamic risk and risk consensus.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.outcome_tracker import TRACKED_PATH, _MIN_SAMPLES, load_metrics


IMPACT_PATH = Path(os.environ.get("EW_IMPACT_STATE", "output/system/impact_discovery.json"))
REGISTRY_PATH = Path(os.environ.get("EW_SIGNAL_REGISTRY", "output/system/signal_registry.json"))

# Candidate data sources / strategies to evaluate (measured lift when data exists)
CANDIDATE_SOURCES: Tuple[Dict[str, str], ...] = (
  {"id": "ew_impulse_valid", "category": "structure", "desc": "R1/R2/R3 impulse valid"},
  {"id": "harmonic_in_zone", "category": "structure", "desc": "Harmonic PRZ overlap"},
  {"id": "supertrend_aligned", "category": "tv_oss", "desc": "Supertrend direction match"},
  {"id": "adx_strong_trend", "category": "tv_oss", "desc": "ADX > 25 trend aligned"},
  {"id": "bb_favorable", "category": "tv_oss", "desc": "Bollinger %B favorable side"},
  {"id": "chandelier_aligned", "category": "tv_oss", "desc": "Chandelier Exit confirms Supertrend"},
  {"id": "ttm_squeeze_release", "category": "tv_oss", "desc": "TTM Squeeze release aligned with direction"},
  {"id": "vwap_anchor_favorable", "category": "tv_oss", "desc": "VWAP anchor favors entry side"},
  {"id": "cmf_flow_aligned", "category": "tv_oss", "desc": "Chaikin MF accumulation supports direction"},
  {"id": "aroon_trend_emerge", "category": "tv_oss", "desc": "Aroon spread confirms trend emergence"},
  {"id": "rsi_stack_bias", "category": "indicator", "desc": "Multi-TF RSI stack agrees"},
  {"id": "funding_carry", "category": "derivatives", "desc": "Funding rate favors direction"},
  {"id": "fear_greed_contrarian", "category": "sentiment", "desc": "Extreme fear long / greed short"},
  {"id": "social_forum_validated", "category": "sentiment", "desc": "Forum strategy passed executive validation"},
  {"id": "social_forum_rejected", "category": "sentiment", "desc": "Forum hype rejected by consensus"},
  {"id": "btc_correlation_filter", "category": "macro", "desc": "BTC correlation alignment"},
  {"id": "orderbook_imbalance", "category": "microstructure", "desc": "Bid/ask imbalance supports trade"},
  {"id": "hist_pair_tf_boost", "category": "feedback", "desc": "Strong tracked pair×TF history"},
  {"id": "probe_only_sizing", "category": "risk", "desc": "Honest probe tier half-size"},
)


def _baseline_win_rate(closed: List[dict]) -> float:
  wins = sum(1 for s in closed if s.get("status") == "tp1_hit")
  losses = sum(1 for s in closed if s.get("status") == "sl_hit")
  return wins / (wins + losses) if (wins + losses) else 0.5


def _bucket_stats(items: List[dict]) -> dict:
  wins = sum(1 for s in items if s.get("status") == "tp1_hit")
  losses = sum(1 for s in items if s.get("status") == "sl_hit")
  decided = wins + losses
  return {
    "n": len(items),
    "wins": wins,
    "losses": losses,
    "decided": decided,
    "win_rate": round(wins / decided, 3) if decided else None,
  }


def _lift(wr: Optional[float], baseline: float) -> Optional[float]:
  if wr is None:
    return None
  return round(wr - baseline, 3)


def discover_impact_factors(state: Optional[dict] = None) -> Dict[str, Any]:
  """
  Attribute win rate lift to observable setup dimensions.
  Returns ranked factors — positive lift = game-changer candidates.
  """
  if state is None:
    if not TRACKED_PATH.exists():
      return {"factors": [], "baseline_wr": None, "sample_size": 0}
    state = json.loads(TRACKED_PATH.read_text(encoding="utf-8"))

  closed = [
    s for s in state.get("closed", [])
    if s.get("status") in ("tp1_hit", "sl_hit")
  ]
  if len(closed) < _MIN_SAMPLES:
    return {"factors": [], "baseline_wr": None, "sample_size": len(closed)}

  baseline = _baseline_win_rate(closed)
  factors: List[dict] = []

  def _add_factor(name: str, category: str, items: List[dict], meta: Optional[dict] = None):
    stats = _bucket_stats(items)
    if stats["decided"] < _MIN_SAMPLES:
      return
    lift = _lift(stats["win_rate"], baseline)
    factors.append({
      "factor": name,
      "category": category,
      "win_rate": stats["win_rate"],
      "lift_vs_baseline": lift,
      "n": stats["decided"],
      "wins": stats["wins"],
      "losses": stats["losses"],
      "impact_score": round(abs(lift or 0) * min(stats["decided"], 50) ** 0.5, 3) if lift else 0,
      **(meta or {}),
    })

  # Timeframe — often the hidden king
  by_tf: Dict[str, List[dict]] = defaultdict(list)
  for s in closed:
    by_tf[s.get("timeframe", "?")].append(s)
  for tf, items in by_tf.items():
    _add_factor(f"tf:{tf}", "timeframe", items)

  # Direction
  for direction in ("LONG", "SHORT", "BULL", "BEAR"):
    items = [s for s in closed if s.get("direction", "").upper() in (direction,)]
    if items:
      _add_factor(f"dir:{direction}", "direction", items)

  # Honest tier
  for tier in ("full", "probe", "none"):
    items = [s for s in closed if s.get("honest_execution_tier") == tier]
    _add_factor(f"honest:{tier}", "honesty_tier", items)

  # GTC tier
  for tier in ("executable", "monitor"):
    items = [s for s in closed if s.get("gtc_tier") == tier]
    _add_factor(f"gtc:{tier}", "export_tier", items)

  # Wave structure keywords
  structures: Dict[str, List[dict]] = defaultdict(list)
  for s in closed:
    ws = (s.get("wave_structure") or "unknown").split("(")[0].strip() or "unknown"
    structures[ws].append(s)
  for ws, items in structures.items():
    if len(items) >= _MIN_SAMPLES:
      _add_factor(f"wave:{ws}", "ew_structure", items)

  # Consensus alignment
  for cons in ("BULL", "BEAR", "NEUTRAL"):
    items = [
      s for s in closed
      if (s.get("consensus") or "").upper() == cons
      and s.get("direction", "").upper() in (cons, "LONG" if cons == "BULL" else "SHORT", "BULL", "BEAR")
    ]
    if items:
      _add_factor(f"consensus_aligned:{cons}", "consensus", items)

  # Tier combos (hidden edge: full + 4h etc.)
  combos: Dict[str, List[dict]] = defaultdict(list)
  for s in closed:
    key = f"{s.get('timeframe')}|{s.get('honest_execution_tier')}"
    combos[key].append(s)
  for key, items in combos.items():
    if len(items) >= _MIN_SAMPLES:
      _add_factor(f"combo:{key}", "combo", items)

  factors.sort(key=lambda x: -x.get("impact_score", 0))

  boosts = [f for f in factors if (f.get("lift_vs_baseline") or 0) > 0.05]
  penalties = [f for f in factors if (f.get("lift_vs_baseline") or 0) < -0.05]
  boosts.sort(key=lambda x: -x["lift_vs_baseline"])
  penalties.sort(key=lambda x: x["lift_vs_baseline"])

  return {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "baseline_wr": round(baseline, 3),
    "sample_size": len(closed),
    "factors": factors,
    "top_boosts": boosts[:8],
    "top_penalties": penalties[:8],
    "hidden_gems": _find_hidden_gems(factors, baseline),
  }


def _find_hidden_gems(factors: List[dict], baseline: float) -> List[dict]:
  """
  High lift but lower sample — worth watching / paper validating.
  """
  gems = []
  for f in factors:
    lift = f.get("lift_vs_baseline") or 0
    n = f.get("n", 0)
    if lift > 0.08 and 3 <= n < 20:
      gems.append({**f, "note": "high lift, low n — validate before full weight"})
    elif lift > 0.12 and n >= 20:
      gems.append({**f, "note": "proven edge — promote to active signal"})
  return gems[:10]


def build_balanced_weights(discovery: dict, *, max_active: int = 5) -> Dict[str, Any]:
  """
  Balanced tweaking: cap how many factors move risk; dampen extreme lifts.
  No single factor > ±12% risk adjustment.
  """
  max_adj = float(os.environ.get("EW_MAX_FACTOR_ADJ", "0.12"))
  weights: Dict[str, float] = {}
  notes: List[str] = []

  penalty_slots = max(1, max_active // 3)
  boost_slots = max(1, max_active - penalty_slots)

  for f in discovery.get("top_boosts", [])[:boost_slots]:
    lift = f.get("lift_vs_baseline") or 0
    adj = min(max_adj, lift * 0.5)  # half the lift → risk boost
    weights[f["factor"]] = round(adj, 4)
    notes.append(f"boost {f['factor']}: +{adj:.1%} risk (lift {lift:+.1%}, n={f['n']})")

  for f in discovery.get("top_penalties", [])[:penalty_slots]:
    if len(weights) >= max_active:
      break
    lift = f.get("lift_vs_baseline") or 0
    adj = max(-max_adj, lift * 0.5)
    weights[f["factor"]] = round(adj, 4)
    notes.append(f"penalty {f['factor']}: {adj:.1%} risk (lift {lift:+.1%}, n={f['n']})")

  total_abs = sum(abs(v) for v in weights.values())
  if total_abs > max_adj * 2:
    scale = (max_adj * 2) / total_abs
    weights = {k: round(v * scale, 4) for k, v in weights.items()}
    notes.append(f"rebalanced: total exposure capped (scale={scale:.2f})")

  return {
    "weights": weights,
    "max_single_adj": max_adj,
    "active_count": len(weights),
    "notes": notes,
  }


def rank_data_sources(discovery: dict, metrics: Optional[dict] = None) -> List[dict]:
  """
  Rank candidate external data sources by measured + inferred impact.
  """
  metrics = metrics or load_metrics()
  by_tf = metrics.get("by_timeframe") or {}
  ranked = []

  for src in CANDIDATE_SOURCES:
    inferred_lift = 0.0
    evidence = "theoretical"
    if src["category"] == "timeframe" and by_tf:
      evidence = "measured via TF attribution"
      inferred_lift = 0.10
    if src["id"] == "hist_pair_tf_boost":
      evidence = "measured — outcome_tracker feedback active"
      inferred_lift = 0.08
    if src["id"] in ("supertrend_aligned", "adx_strong_trend"):
      evidence = "TV OSS wired — validate via forward test"
      inferred_lift = 0.06
    if src["id"] == "funding_carry":
      evidence = "data_hub funding — high carry potential"
      inferred_lift = 0.05
    if src["id"] == "fear_greed_contrarian":
      evidence = "web_intel — contrarian at extremes"
      inferred_lift = 0.04
    if src["id"] == "social_forum_validated":
      try:
        from engine.social_strategy_validation import load_social_validation

        sv = load_social_validation()
        if sv.get("validated_strategies"):
          evidence = "social validation consensus — promoted strategies"
          inferred_lift = 0.07
      except Exception:
        pass
    if src["id"] == "social_forum_rejected":
      evidence = "social validation — hype filtered out"
      inferred_lift = -0.02

    for f in discovery.get("top_boosts", []):
      if src["category"] in f.get("factor", "") or src["id"].split("_")[0] in f.get("factor", ""):
        inferred_lift = max(inferred_lift, f.get("lift_vs_baseline") or 0)

    ranked.append({
      **src,
      "inferred_lift": round(inferred_lift, 3),
      "evidence": evidence,
      "priority": "high" if inferred_lift >= 0.08 else "medium" if inferred_lift >= 0.04 else "low",
    })

  ranked.sort(key=lambda x: -x["inferred_lift"])
  return ranked


def run_impact_discovery() -> Dict[str, Any]:
  """Full discovery pass + balanced weights + registry update."""
  discovery = discover_impact_factors()
  balance = build_balanced_weights(discovery)
  sources = rank_data_sources(discovery)
  metrics = load_metrics()

  report = {
    "discovery": discovery,
    "balanced_weights": balance,
    "data_sources": sources,
    "metrics_snapshot": {
      "overall_wr": (metrics.get("overall") or {}).get("win_rate"),
      "open": metrics.get("open_count"),
    },
    "recommendations": _synthesize_recommendations(discovery, balance, sources),
  }

  _save_impact(report)
  _save_registry(balance, sources)
  return report


def _synthesize_recommendations(discovery: dict, balance: dict, sources: List[dict]) -> List[str]:
  recs = []
  baseline = discovery.get("baseline_wr")
  if baseline is not None and baseline < 0.55:
    recs.append("Global win rate below 55% — prioritize loss reduction over new entries")

  for gem in discovery.get("hidden_gems", [])[:3]:
    recs.append(f"Validate gem: {gem['factor']} (lift {gem.get('lift_vs_baseline', 0):+.1%}, n={gem['n']})")

  for src in sources[:3]:
    if src["priority"] == "high":
      recs.append(f"Invest in data source: {src['id']} — {src['desc']}")

  for note in balance.get("notes", [])[:3]:
    recs.append(f"Active tweak: {note}")

  if not recs:
    recs.append("Maintain balanced posture — no dominant factor shift detected")
  return recs


def _save_impact(report: dict) -> None:
  IMPACT_PATH.parent.mkdir(parents=True, exist_ok=True)
  IMPACT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def _save_registry(balance: dict, sources: List[dict]) -> None:
  REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
  REGISTRY_PATH.write_text(
    json.dumps({
      "updated": datetime.now(timezone.utc).isoformat(),
      "active_weights": balance.get("weights", {}),
      "data_sources": sources[:12],
    }, indent=2),
    encoding="utf-8",
  )


def load_impact_report() -> dict:
  if not IMPACT_PATH.exists():
    return {}
  try:
    return json.loads(IMPACT_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}


def lookup_factor_adjustment(factor_key: str) -> float:
  """Risk adjustment for a matched factor key (from registry)."""
  reg = load_impact_report()
  weights = (reg.get("balanced_weights") or {}).get("weights") or {}
  return float(weights.get(factor_key, 0))


def match_setup_factors(
  *,
  timeframe: str = "",
  direction: str = "",
  honest_tier: str = "",
  gtc_tier: str = "",
  wave_structure: str = "",
) -> List[str]:
  """Build factor keys for a live setup to apply balanced weights."""
  keys = []
  if timeframe:
    keys.append(f"tf:{timeframe}")
  if direction:
    keys.append(f"dir:{direction.upper()}")
  if honest_tier:
    keys.append(f"honest:{honest_tier}")
  if gtc_tier:
    keys.append(f"gtc:{gtc_tier}")
  if wave_structure:
    ws = wave_structure.split("(")[0].strip()
    keys.append(f"wave:{ws}")
  if timeframe and honest_tier:
    keys.append(f"combo:{timeframe}|{honest_tier}")
  return keys
