"""
Always-on smart risk stack — single policy for the whole execution pipeline.

Defaults (override only with EW_ALWAYS_SMART_RISK=0):
- Dynamic risk management (vol, TV, history, drawdown)
- DCA pyramid 10 / 20 / 30 / 40
- Smart dynamic stop-loss (structure + zone + ATR)
- Smart dynamic targets (R-multiples by TF, 50/25/25 exits)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from core.risk import DCA_PROFILE_PYRAMID, DCA_SPLITS, dynamic_stop, dynamic_targets

SMART_SL_ARCH = "smart_dynamic_sl"
SMART_TP_ARCH = "smart_dynamic_tp"
POLICY_TAG = "always_smart_risk_v1"


def always_smart_enabled() -> bool:
  return os.environ.get("EW_ALWAYS_SMART_RISK", "1").lower() not in ("0", "false", "no")


def require_pyramid_dca() -> bool:
  return always_smart_enabled()


def default_dca_profile() -> str:
  return DCA_PROFILE_PYRAMID


def dca_splits() -> List[int]:
  return list(DCA_SPLITS)


def select_dca_profile(
  symbol: str,
  tf: str,
  result: dict,
  ctx: Any,
) -> Tuple[str, str]:
  """Always pyramid 10/20/30/40 unless legacy mode."""
  if require_pyramid_dca():
    return default_dca_profile(), "always smart pyramid 10/20/30/40"
  from engine.execution_advanced import _legacy_select_dca_profile

  return _legacy_select_dca_profile(symbol, tf, result, ctx)


def compute_dynamic_risk_context(
  *,
  symbol: str = "",
  timeframe: str = "",
  direction: str = "",
  df=None,
  tv_score: Optional[int] = None,
  readiness_score: Optional[int] = None,
  hist_win_rate: Optional[float] = None,
  hist_n: int = 0,
  gtc_tier: str = "executable",
  honest_tier: str = "probe",
  wave_structure: str = "",
) -> Dict[str, Any]:
  from engine.dynamic_risk import compute_risk_multiplier

  return compute_risk_multiplier(
    symbol=symbol,
    timeframe=timeframe,
    direction=direction,
    df=df,
    tv_score=tv_score,
    readiness_score=readiness_score,
    hist_win_rate=hist_win_rate,
    hist_n=hist_n,
    gtc_tier=gtc_tier,
    honest_tier=honest_tier,
    wave_structure=wave_structure,
  )


def apply_account_risk_pct(
  base_pct: float,
  risk_ctx: Optional[dict] = None,
) -> float:
  from engine.dynamic_risk import apply_dynamic_account_risk

  if risk_ctx is None:
    risk_ctx = {"mult": 1.0, "enabled": False, "factors": []}
  if always_smart_enabled() and not risk_ctx.get("enabled"):
    risk_ctx = {**risk_ctx, "enabled": True, "mult": risk_ctx.get("mult", 1.0)}
  return apply_dynamic_account_risk(base_pct, risk_ctx)


def resolve_smart_stop(
  direction: str,
  entry: float,
  atr: float,
  s_low: float,
  s_high: float,
  cfg: dict,
  zone_low: float,
  zone_high: float,
  reused: Optional[dict] = None,
  *,
  timeframe: str = "",
  ladder_legs: Optional[List[dict]] = None,
) -> dict:
  """Force smart_dynamic_sl — recompute if reused stop is not smart."""
  smart = reused and isinstance(reused, dict) and reused.get("architecture") == SMART_SL_ARCH
  if smart and reused.get("price") is not None:
    return {**reused, "price": float(reused["price"])}
  return dynamic_stop(
    direction, entry, atr, s_low, s_high, cfg.get("atr_mult_sl", 1.0),
    zone_low=zone_low, zone_high=zone_high,
    max_stop_atr=cfg.get("max_stop_atr", 5.0),
    timeframe=timeframe or None,
    ladder_legs=ladder_legs,
  )


def resolve_smart_targets(
  direction: str,
  entry: float,
  atr: float,
  *,
  harmonic_prz=None,
  c_target_100=None,
  c_target_161=None,
  stop_price: float,
  zone_low: float,
  zone_high: float,
  timeframe: str = "",
  structure_low: float = 0.0,
  structure_high: float = 0.0,
) -> List[dict]:
  targets = dynamic_targets(
    direction, entry, atr,
    harmonic_prz=harmonic_prz,
    c_target_100=c_target_100,
    c_target_161=c_target_161,
    stop_price=stop_price,
    zone_low=zone_low,
    zone_high=zone_high,
    timeframe=timeframe or None,
    structure_low=structure_low,
    structure_high=structure_high,
  )
  for t in targets:
    t.setdefault("architecture", SMART_TP_ARCH)
  return targets


def stamp_row_policy(row: dict) -> dict:
  """Annotate export row with always-on smart risk metadata."""
  row = dict(row)
  row["smart_risk_policy"] = POLICY_TAG
  row["dca_splits_pct"] = ",".join(str(x) for x in dca_splits())
  row["dca_profile"] = default_dca_profile()
  row.setdefault("stop_architecture", SMART_SL_ARCH)
  row.setdefault("dynamic_risk_mult", row.get("dynamic_risk_mult") or 1.0)
  for i, key in enumerate(("tp1", "tp2", "tp3"), start=1):
    if row.get(key):
      row.setdefault(f"tp{i}_architecture", SMART_TP_ARCH)
  if row.get("tp1_exit_pct") is None:
    row["tp1_exit_pct"] = 50
  if row.get("tp2_exit_pct") is None:
    row["tp2_exit_pct"] = 25
  if row.get("tp3_exit_pct") is None:
    row["tp3_exit_pct"] = 25
  return row


def validate_row_policy(row: dict) -> Tuple[bool, List[str]]:
  """Returns (ok, issues) — used by paper sim / execution gates."""
  if not always_smart_enabled():
    return True, []
  issues: List[str] = []
  profile = str(row.get("dca_profile") or "")
  if profile and profile != default_dca_profile():
    issues.append(f"dca_profile={profile} (expected {default_dca_profile()})")
  splits = str(row.get("dca_splits_pct") or "")
  expected = ",".join(str(x) for x in dca_splits())
  if splits and splits != expected:
    issues.append(f"dca_splits={splits} (expected {expected})")
  if row.get("stop_architecture") and row.get("stop_architecture") != SMART_SL_ARCH:
    issues.append(f"stop_architecture={row.get('stop_architecture')}")
  if not row.get("stop_loss") and not row.get("stop_loss_price"):
    issues.append("missing_stop_loss")
  if not row.get("tp1"):
    issues.append("missing_tp1")
  return len(issues) == 0, issues
