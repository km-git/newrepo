"""Multi-engine Elliott Wave consensus from GitHub tools + internal validator."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from cache.disk_cache import get_cache
from core.ewa_adapter import scan_ewa
from core.impulse import validate_impulse
from core.taew_adapter import scan_taew_fib


def _best_internal_vote(mws: List[dict], engine_id: str) -> dict:
  """Scan sliding windows; return best passing impulse or last failing direction."""
  best = None
  for start in range(max(0, len(mws) - 4)):
    candidate = mws[start : start + 5]
    if len(candidate) < 5:
      continue
    val = validate_impulse(candidate)
    if val["passes"]:
      return {
        "engine": engine_id,
        "source": "internal/core/impulse.py",
        "direction": val["direction"],
        "valid": True,
        "confidence": 0.85,
        "detail": f"R1/R2/R3 pass, sizes={val['sizes']}",
      }
    if best is None or (val["direction"] != "AMBIGUOUS" and val["direction"] != "n/a"):
      best = val

  if best and best.get("direction") not in ("AMBIGUOUS", "n/a"):
    conf = 0.35 if best.get("violations") else 0.25
    return {
      "engine": engine_id,
      "source": "internal/core/impulse.py",
      "direction": best["direction"],
      "valid": False,
      "confidence": conf,
      "detail": f"violations: {best.get('violations', [])}",
    }
  return {
    "engine": engine_id,
    "source": "internal/core/impulse.py",
    "direction": "NEUTRAL",
    "valid": False,
    "confidence": 0.0,
    "detail": "no 5-wave candidate",
  }


def _ewa_votes(ewa_result: dict) -> List[dict]:
  votes: List[dict] = []
  if not ewa_result.get("available"):
    return [{
      "engine": "ewa",
      "source": "github.com/drstevendev/ElliottWaveAnalyzer",
      "direction": "NEUTRAL",
      "valid": False,
      "confidence": 0.0,
      "detail": ewa_result.get("error", "unavailable"),
    }]

  for key, label, conf in [
    ("impulse", "ewa_impulse", 0.80),
    ("leading_diagonal", "ewa_diagonal", 0.70),
    ("correction", "ewa_correction", 0.65),
  ]:
    hit = ewa_result.get(key)
    if hit:
      votes.append({
        "engine": label,
        "source": ewa_result["source"],
        "direction": hit["direction"],
        "valid": True,
        "confidence": conf,
        "detail": f"{hit['rule']} config={hit.get('wave_config')}",
      })
  if not votes:
    votes.append({
      "engine": "ewa",
      "source": ewa_result["source"],
      "direction": "NEUTRAL",
      "valid": False,
      "confidence": 0.0,
      "detail": f"no match in {ewa_result.get('configs_tried', 0)} configs",
    })
  return votes


def _taew_vote(taew_result: dict) -> dict:
  if not taew_result.get("available"):
    return {
      "engine": "taew_fib",
      "source": "github.com/DrEdwardPCB/python-taew",
      "direction": "NEUTRAL",
      "valid": False,
      "confidence": 0.0,
      "detail": taew_result.get("error", "unavailable"),
    }
  return {
    "engine": "taew_fib",
    "source": taew_result["source"],
    "direction": taew_result["direction"] if taew_result["direction"] != "AMBIGUOUS" else "NEUTRAL",
    "valid": taew_result["valid"],
    "confidence": round(0.45 + taew_result["fib_score"] * 0.40, 2),
    "detail": f"fib_score={taew_result['fib_score']} checks={taew_result['fib_checks']}",
  }


def build_consensus(
  data: Dict[str, pd.DataFrame],
  adaptive: Dict[str, dict],
  symbol: str,
  timeframes: Optional[List[str]] = None,
) -> dict:
  """
  Run all EW engines and compute direction consensus + confidence boost.
  Engines: internal R1/R2/R3, ElliottWaveAnalyzer, python-taew fib.
  """
  cache = get_cache()
  tfs = timeframes or ["1d", "4h", "15m"]
  votes: List[dict] = []

  for tf in tfs:
    if tf not in adaptive:
      continue
    mws = adaptive[tf]["monowaves"]
    votes.append(_best_internal_vote(mws, f"internal_{tf}"))

  primary_tf = "1d" if "1d" in adaptive else tfs[0]
  primary_mws = adaptive.get(primary_tf, {}).get("monowaves", [])

  def _ewa_compute():
    return scan_ewa(data[primary_tf], up_to=6, max_configs=120)

  ewa_result, ewa_hit = cache.get_or_compute(
    "ewa_consensus",
    _ewa_compute,
    symbol,
    primary_tf,
    len(data[primary_tf]),
    round(float(data[primary_tf]["Close"].iloc[-1]), 2),
  )
  if ewa_hit:
    print(f"[cache] HIT ewa_consensus {symbol} {primary_tf}")
  votes.extend(_ewa_votes(ewa_result))

  taew_result = scan_taew_fib(primary_mws)
  votes.append(_taew_vote(taew_result))

  # Also run taew on 15m if different
  if "15m" in adaptive and "15m" != primary_tf:
    taew_15m = scan_taew_fib(adaptive["15m"]["monowaves"])
    votes.append({**_taew_vote(taew_15m), "engine": "taew_fib_15m"})

  # Aggregate
  bull_w = bear_w = neutral_w = 0.0
  valid_engines = 0
  for v in votes:
    d = v["direction"]
    w = v["confidence"] if v["valid"] else v["confidence"] * 0.5
    if d == "BULL":
      bull_w += w
    elif d == "BEAR":
      bear_w += w
    else:
      neutral_w += w
    if v["valid"]:
      valid_engines += 1

  total = bull_w + bear_w + neutral_w
  if bull_w > bear_w:
    consensus_direction = "BULL"
    agree_weight = bull_w
  elif bear_w > bull_w:
    consensus_direction = "BEAR"
    agree_weight = bear_w
  else:
    consensus_direction = "NEUTRAL"
    agree_weight = max(bull_w, bear_w)

  consensus_score = round(agree_weight / total, 3) if total > 0 else 0.0
  agreeing = sum(
    1 for v in votes
    if v["direction"] == consensus_direction and v["direction"] != "NEUTRAL"
  )
  directional_votes = [v for v in votes if v["direction"] in ("BULL", "BEAR")]
  agreement_pct = round(agreeing / max(len(directional_votes), 1) * 100, 1)

  divergences = []
  for v in votes:
    if v["direction"] in ("BULL", "BEAR") and v["direction"] != consensus_direction:
      divergences.append(f"{v['engine']}: {v['direction']} ({v['detail'][:60]})")

  if consensus_score >= 0.65 and agreement_pct >= 60:
    conviction = "high"
  elif consensus_score >= 0.45:
    conviction = "medium"
  else:
    conviction = "low"

  confidence_boost = round((consensus_score - 0.5) * 0.20, 3)

  print(
    f"[consensus] direction={consensus_direction} score={consensus_score} "
    f"agreement={agreement_pct}% engines_valid={valid_engines}/{len(votes)}"
  )

  return {
    "consensus_direction": consensus_direction,
    "consensus_score": consensus_score,
    "agreement_pct": agreement_pct,
    "conviction": conviction,
    "confidence_boost": confidence_boost,
    "engines_run": len(votes),
    "engines_valid": valid_engines,
    "votes": votes,
    "divergences": divergences,
    "github_tools_used": [
      "github.com/drstevendev/ElliottWaveAnalyzer",
      "github.com/DrEdwardPCB/python-taew",
    ],
  }
