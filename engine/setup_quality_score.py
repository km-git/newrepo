"""Unified Setup Quality Score (SQS) — rank pair×TF exports by confluence + expectancy."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Component weights (sum = 1.0)
WEIGHT_STRUCTURE = 0.25
WEIGHT_MTF = 0.20
WEIGHT_EXPECTANCY = 0.25
WEIGHT_READINESS = 0.15
WEIGHT_HISTORICAL = 0.10
WEIGHT_DCA = 0.05

SQS_TIER_EXECUTE = 75
SQS_TIER_STANDBY = 60
SQS_TIER_WATCH = 45

SQS_RANKED_CSV = Path("output/latest_sqs_ranked_setups.csv")

RANKED_FIELDS = [
  "sqs_rank",
  "sqs_score",
  "sqs_tier",
  "sqs_action",
  "symbol",
  "timeframe",
  "direction",
  "gtc_tier",
  "honest_execution_tier",
  "executive_verdict",
  "executive_action",
  "executive_score",
  "wae",
  "stop_distance_pct",
  "l1_stop_distance_pct",
  "dca_sl_resolvable",
  "rr_tp2",
  "readiness_score",
  "agreement_pct",
  "hist_win_rate",
  "hist_n",
  "sqs_tags",
]


def _f(row: dict, key: str, default: float = 0.0) -> float:
  try:
    v = row.get(key)
    if v is None or v == "":
      return default
    return float(v)
  except (TypeError, ValueError):
    return default


def _i(row: dict, key: str, default: int = 0) -> int:
  try:
    v = row.get(key)
    if v is None or v == "":
      return default
    return int(float(v))
  except (TypeError, ValueError):
    return default


def _yn(row: dict, key: str) -> bool:
  return str(row.get(key) or "").upper() in ("Y", "YES", "TRUE", "1")


def sqs_tier(score: float) -> str:
  if score >= SQS_TIER_EXECUTE:
    return "EXECUTE"
  if score >= SQS_TIER_STANDBY:
    return "STANDBY"
  if score >= SQS_TIER_WATCH:
    return "WATCH"
  return "SKIP"


def sqs_action(score: float, row: dict) -> str:
  """Action label aligned with executive + SQS bands."""
  tier = sqs_tier(score)
  exec_action = str(row.get("executive_action") or "")
  gtc_tier = str(row.get("gtc_tier") or "")
  if str(row.get("geometry_valid") or "Y").upper() != "Y":
    return "SKIP"
  if gtc_tier == "watch" or exec_action.startswith("WATCH"):
    return "WATCH_ALERT" if tier != "SKIP" else "SKIP"
  if tier == "EXECUTE":
    if exec_action in ("EXECUTE_NOW", "EXECUTE_CAUTION", "SCALE_IN"):
      return exec_action
    return "EXECUTE_NOW"
  if tier == "STANDBY":
    if exec_action in ("STANDBY_LIMIT", "SCALE_IN", "EXECUTE_CAUTION"):
      return exec_action
    return "STANDBY_LIMIT"
  if tier == "WATCH":
    if exec_action.startswith("WATCH"):
      return exec_action
    return "WATCH_ALERT"
  return "SKIP"


def _structure_score(row: dict) -> Tuple[float, List[str]]:
  score = 0.0
  tags: List[str] = []

  if _yn(row, "wave_valid"):
    score += 40
    tags.append("impulse_valid")
  else:
    struct = str(row.get("wave_structure") or "").lower()
    if struct and not struct.startswith("invalid"):
      score += 12
      tags.append("structure_ok")

  if _yn(row, "in_kill_zone"):
    score += 30
    tags.append("in_zone")
  else:
    verdict = str(row.get("executive_verdict") or "")
    if verdict == "GO":
      score += 18
      tags.append("verdict_go")
    elif verdict in ("STAGED_GO", "CONDITIONAL_GO"):
      score += 12
      tags.append("verdict_staged")
    elif verdict == "STANDBY_ORDERS":
      score += 8
      tags.append("harmonic_standby")

  if row.get("gtc_tier") == "executable":
    score += 10
    tags.append("executable")
  elif row.get("gtc_tier") == "monitor":
    score += 5

  return min(100.0, score), tags


def _mtf_score(row: dict) -> Tuple[float, List[str]]:
  score = 0.0
  tags: List[str] = []
  agreement = _f(row, "agreement_pct")
  score += min(55.0, agreement * 0.75)
  if agreement >= 70:
    tags.append(f"ew_agree_{agreement:.0f}%")
  elif agreement >= 55:
    tags.append(f"ew_moderate_{agreement:.0f}%")

  direction = str(row.get("direction") or "").upper()
  consensus = str(row.get("consensus") or "").upper()
  aligned = (
    consensus in ("NEUTRAL", "")
    or (direction == "LONG" and consensus in ("LONG", "BULL"))
    or (direction == "SHORT" and consensus in ("SHORT", "BEAR"))
  )
  if aligned:
    score += 35
    tags.append("consensus_aligned")
  else:
    score += 8
    tags.append("consensus_mixed")

  tv = _i(row, "tv_oss_score") or _i(row, "tv_composite_score")
  if tv >= 70:
    score += 10
    tags.append(f"tv_{tv}")
  elif tv >= 58:
    score += 5

  return min(100.0, score), tags


def _expectancy_score(row: dict) -> Tuple[float, List[str]]:
  score = 0.0
  tags: List[str] = []
  wr = row.get("hist_win_rate")
  n = _i(row, "hist_n")
  scope = str(row.get("hist_scope") or "none")
  pair_evidence = scope == "pair_tf"
  if wr is not None and n >= 3 and pair_evidence:
    wr_f = float(wr)
    score += min(55.0, wr_f * 80.0)
    if wr_f >= 0.65:
      tags.append(f"hist_wr_{wr_f:.0%}")
    elif wr_f >= 0.55:
      tags.append(f"hist_ok_{wr_f:.0%}")
    elif wr_f < 0.45:
      score -= 15
      tags.append(f"hist_weak_{wr_f:.0%}")

  rr = _f(row, "rr_tp2")
  min_rr = _f(row, "min_rr", 1.2)
  if rr >= min_rr * 1.5:
    score += 25
    tags.append(f"rr_strong_{rr:.1f}")
  elif rr >= min_rr:
    score += 15
    tags.append(f"rr_ok_{rr:.1f}")
  elif rr > 0:
    score += 5

  tp1_r = _f(row, "tp1_r_multiple")
  if tp1_r > 0 and wr is not None and n >= 3 and pair_evidence:
    partial = float(__import__("os").environ.get("EW_TP1_EXIT_PCT", "50")) / 100.0
    exp = float(wr) * tp1_r * partial - (1.0 - float(wr))
    if exp > 0:
      score += min(25.0, 10.0 + exp * 20.0)
      tags.append(f"+EV_{exp:.2f}R")
    else:
      score -= 10
      tags.append(f"-EV_{exp:.2f}R")
  elif wr is not None and n >= 3:
    tags.append(f"{scope}_context_only")

  exec_score = _i(row, "executive_score")
  if exec_score > 0:
    score += min(20.0, exec_score * 0.2)
    tags.append(f"exec_{exec_score}")

  return min(100.0, max(0.0, score)), tags


def _readiness_score(row: dict) -> Tuple[float, List[str]]:
  r = _i(row, "readiness_score")
  tags: List[str] = []
  if r >= 72:
    tags.append(f"ready_{r}")
  elif r >= 58:
    tags.append(f"ready_moderate_{r}")
  return min(100.0, float(r)), tags


def _historical_score(row: dict) -> Tuple[float, List[str]]:
  score = 40.0
  tags: List[str] = []
  scope = str(row.get("hist_scope") or "none")
  if scope != "pair_tf":
    if scope in ("timeframe", "overall"):
      tags.append(f"{scope}_history_not_pair_edge")
    return score, tags

  action = str(row.get("hist_action") or "")
  if action == "boost":
    score += 35
    tags.append("hist_boost")
  elif action == "downgrade":
    score -= 35
    tags.append("hist_downgrade")
  elif action == "caution":
    score -= 15
    tags.append("hist_caution")

  wr = row.get("hist_win_rate")
  n = _i(row, "hist_n")
  if wr is not None and n >= 5:
    wr_f = float(wr)
    if wr_f >= 0.60:
      score += 25
    elif wr_f >= 0.55:
      score += 12
    elif wr_f < 0.42:
      score -= 20

  return min(100.0, max(0.0, score)), tags


def _dca_score(row: dict) -> Tuple[float, List[str]]:
  score = 50.0
  tags: List[str] = []
  if str(row.get("dca_sl_resolvable") or "").upper() == "Y":
    score = 95.0
    tags.append("dca_resolvable")
  else:
    reduction = _f(row, "dca_stop_reduction_pct")
    if reduction >= 0.7:
      score = 75.0
      tags.append(f"dca_red_{reduction:.1f}pp")
    elif reduction >= 0.3:
      score = 60.0
    l1 = _f(row, "l1_stop_distance_pct")
    wae = _f(row, "stop_distance_pct")
    wide_thr = _f(row, "dca_sl_wide_threshold_pct", 3.0)
    if l1 > wide_thr and wae > _f(row, "dca_sl_target_pct", 2.5):
      score -= 20
      tags.append("wide_l1_unresolved")

  return min(100.0, max(0.0, score)), tags


def compute_setup_quality_score(row: dict) -> Dict[str, Any]:
  """Return SQS score 0–100 plus tier, action, component breakdown."""
  if row.get("row_type") not in (None, "primary", ""):
    return {
      "sqs_score": 0,
      "sqs_tier": "SKIP",
      "sqs_action": "SKIP",
      "sqs_tags": "non_primary",
      "sqs_components_json": "{}",
    }

  hard_errors: List[str] = []
  if str(row.get("geometry_valid") or "Y").upper() != "Y":
    hard_errors.append("invalid_geometry")
  entry = _f(row, "wae")
  stop = _f(row, "stop_loss")
  rr = _f(row, "rr_tp2")
  min_rr = _f(row, "min_rr", 1.2)
  direction = str(row.get("direction") or "").upper()
  targets = [_f(row, f"tp{i}") for i in (1, 2, 3)]
  if entry <= 0 or stop <= 0 or any(tp <= 0 for tp in targets):
    hard_errors.append("non_positive_trade_level")
  elif direction == "LONG":
    if not (stop < entry < targets[0] <= targets[1] <= targets[2]):
      hard_errors.append("invalid_long_level_order")
  elif direction == "SHORT":
    if not (stop > entry > targets[0] >= targets[1] >= targets[2]):
      hard_errors.append("invalid_short_level_order")
  else:
    hard_errors.append("invalid_direction")
  if rr < min_rr * 0.95 or rr > 5.25:
    hard_errors.append("rr_out_of_bounds")

  if hard_errors:
    return {
      "sqs_score": 0,
      "sqs_tier": "SKIP",
      "sqs_action": "SKIP",
      "sqs_tags": "; ".join(hard_errors),
      "sqs_components_json": "{}",
    }

  s_struct, t_struct = _structure_score(row)
  s_mtf, t_mtf = _mtf_score(row)
  s_exp, t_exp = _expectancy_score(row)
  s_ready, t_ready = _readiness_score(row)
  s_hist, t_hist = _historical_score(row)
  s_dca, t_dca = _dca_score(row)

  total = (
    s_struct * WEIGHT_STRUCTURE
    + s_mtf * WEIGHT_MTF
    + s_exp * WEIGHT_EXPECTANCY
    + s_ready * WEIGHT_READINESS
    + s_hist * WEIGHT_HISTORICAL
    + s_dca * WEIGHT_DCA
  )
  total = round(min(100.0, max(0.0, total)), 1)
  tier = sqs_tier(total)

  # Accuracy labels require setup-level evidence and executable routing.
  # Market-wide/timeframe aggregate history is context, never proof that this pair works.
  hist_scope = str(row.get("hist_scope") or "none")
  hist_n = _i(row, "hist_n")
  gtc_tier = str(row.get("gtc_tier") or "")
  exec_action = str(row.get("executive_action") or "")
  if tier == "EXECUTE" and (hist_scope != "pair_tf" or hist_n < 5):
    tier = "STANDBY"
  if gtc_tier == "watch" or exec_action.startswith("WATCH"):
    tier = "WATCH" if total >= SQS_TIER_WATCH else "SKIP"
  elif gtc_tier == "monitor" and tier == "EXECUTE":
    tier = "STANDBY"

  effective_score = total
  if tier == "STANDBY":
    effective_score = min(effective_score, SQS_TIER_EXECUTE - 0.1)
  elif tier == "WATCH":
    effective_score = min(effective_score, SQS_TIER_STANDBY - 0.1)
  elif tier == "SKIP":
    effective_score = min(effective_score, SQS_TIER_WATCH - 0.1)
  total = round(effective_score, 1)
  action = sqs_action(total, row)
  all_tags = t_struct + t_mtf + t_exp + t_ready + t_hist + t_dca

  components = {
    "structure": round(s_struct, 1),
    "mtf": round(s_mtf, 1),
    "expectancy": round(s_exp, 1),
    "readiness": round(s_ready, 1),
    "historical": round(s_hist, 1),
    "dca": round(s_dca, 1),
  }

  return {
    "sqs_score": total,
    "sqs_tier": tier,
    "sqs_action": action,
    "sqs_tags": "; ".join(all_tags[:12]),
    "sqs_components_json": json.dumps(components, separators=(",", ":")),
  }


def stamp_row_sqs(row: dict) -> dict:
  """Attach SQS fields to an export row (in place)."""
  row.update(compute_setup_quality_score(row))
  return row


def stamp_rows_sqs(rows: List[dict]) -> List[dict]:
  return [stamp_row_sqs(r) for r in rows]


def rank_rows_by_sqs(rows: List[dict], *, primary_only: bool = True) -> List[dict]:
  """Sort rows by sqs_score descending; assign sqs_rank."""
  pool = [r for r in rows if not primary_only or r.get("row_type", "primary") == "primary"]
  stamped = stamp_rows_sqs(pool)
  ranked = sorted(stamped, key=lambda r: (-_f(r, "sqs_score"), r.get("symbol", ""), r.get("timeframe", "")))
  for i, row in enumerate(ranked, start=1):
    row["sqs_rank"] = i
  return ranked


def save_sqs_ranked_csv(
  rows: List[dict],
  path: Optional[Path] = None,
  *,
  min_tier: Optional[str] = None,
  top_n: Optional[int] = None,
) -> Path:
  """Write SQS-ranked setups to CSV."""
  path = path or SQS_RANKED_CSV
  path.parent.mkdir(parents=True, exist_ok=True)
  ranked = rank_rows_by_sqs(rows)
  if min_tier:
    order = {"EXECUTE": 4, "STANDBY": 3, "WATCH": 2, "SKIP": 1}
    floor = order.get(min_tier.upper(), 0)
    ranked = [r for r in ranked if order.get(str(r.get("sqs_tier")), 0) >= floor]
  if top_n:
    ranked = ranked[:top_n]
  with path.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=RANKED_FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(ranked)
  return path


def sqs_summary(rows: List[dict]) -> Dict[str, Any]:
  """Aggregate SQS tier counts for export meta."""
  ranked = rank_rows_by_sqs(rows)
  by_tier: Dict[str, int] = {}
  by_action: Dict[str, int] = {}
  for r in ranked:
    t = str(r.get("sqs_tier") or "SKIP")
    by_tier[t] = by_tier.get(t, 0) + 1
    a = str(r.get("sqs_action") or "SKIP")
    by_action[a] = by_action.get(a, 0) + 1
  top = ranked[:5] if ranked else []
  return {
    "sqs_ranked_count": len(ranked),
    "sqs_by_tier": by_tier,
    "sqs_by_action": by_action,
    "sqs_top5": [
      {
        "rank": r.get("sqs_rank"),
        "symbol": r.get("symbol"),
        "timeframe": r.get("timeframe"),
        "sqs_score": r.get("sqs_score"),
        "sqs_tier": r.get("sqs_tier"),
        "direction": r.get("direction"),
      }
      for r in top
    ],
  }
