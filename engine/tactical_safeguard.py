"""
Tactical safeguard — adaptive, calculative, flexible account protection.

Posture-driven risk: shrink size, prefer defensive DCA, probe-only when stressed.
Goal: safeguard capital first; only scale when proof and drawdown allow.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from core.risk import DCA_PROFILE_30_70, DCA_PROFILE_PYRAMID

POSTURE_DEFENSIVE = "DEFENSIVE"
POSTURE_CAUTIOUS = "CAUTIOUS"
POSTURE_NEUTRAL = "NEUTRAL"
POSTURE_OPPORTUNISTIC = "OPPORTUNISTIC"

POSTURE_SIZE_CAP = {
  POSTURE_DEFENSIVE: 35.0,
  POSTURE_CAUTIOUS: 60.0,
  POSTURE_NEUTRAL: 100.0,
  POSTURE_OPPORTUNISTIC: 100.0,
}

POSTURE_RISK_MULT = {
  POSTURE_DEFENSIVE: 0.50,
  POSTURE_CAUTIOUS: 0.70,
  POSTURE_NEUTRAL: 1.00,
  POSTURE_OPPORTUNISTIC: 1.05,
}


def tactical_safeguard_enabled() -> bool:
  return os.environ.get("EW_TACTICAL_SAFEGUARD", "1").lower() not in ("0", "false", "no")


def _corr_from_result(result: dict) -> float:
  mkt = result.get("step9_market_confluence") or result.get("step9_market_tools") or {}
  corr = (mkt.get("btc_correlation") or {}).get("correlation")
  try:
    return abs(float(corr)) if corr is not None else 0.0
  except (TypeError, ValueError):
    return 0.0


def assess_tactical_posture() -> Dict[str, Any]:
  """
  Score account stress → tactical posture.
  DEFENSIVE: halt proximity, proof failing, deep drawdown
  CAUTIOUS: elevated heat, negative paper P&L, moderate drawdown
  NEUTRAL: normal operations
  OPPORTUNISTIC: proof GO + positive P&L + low drawdown (small boost only)
  """
  if not tactical_safeguard_enabled():
    return {
      "posture": POSTURE_NEUTRAL,
      "score": 50,
      "factors": ["tactical_safeguard_off"],
      "size_cap_pct": 100.0,
      "risk_mult": 1.0,
      "probe_only": False,
    }

  score = 50.0
  factors: List[str] = []
  drawdown_pct = 0.0
  halted = False
  proof_verdict = None
  cumulative_pnl = 0.0
  portfolio_util = 0.0

  try:
    from engine.risk_ops import _load, drawdown_threshold_pct, is_halted

    state = _load()
    drawdown_pct = float(state.get("drawdown_pct") or 0)
    halted = is_halted()
    threshold = drawdown_threshold_pct()
    if halted:
      score -= 40
      factors.append("risk_halted")
    elif drawdown_pct >= threshold * 0.85:
      score -= 30
      factors.append(f"drawdown_{drawdown_pct:.1f}%_critical")
    elif drawdown_pct >= threshold * 0.5:
      score -= 18
      factors.append(f"drawdown_{drawdown_pct:.1f}%_elevated")
    elif drawdown_pct >= threshold * 0.25:
      score -= 8
      factors.append(f"drawdown_{drawdown_pct:.1f}%_watch")
  except Exception:
    pass

  try:
    from engine.paper_forward_tracker import evaluate_proof_verdict, rolling_metrics

    proof = evaluate_proof_verdict()
    proof_verdict = proof.get("verdict")
    cumulative_pnl = float((proof.get("metrics") or {}).get("cumulative_pnl_usd") or 0)
    if proof_verdict == "PROOF_NO_GO":
      score -= 22
      factors.append("paper_proof_no_go")
    elif proof_verdict == "PROOF_PENDING" and cumulative_pnl < 0:
      score -= 10
      factors.append("paper_pnl_negative")
    elif proof_verdict == "PROOF_GO" and cumulative_pnl > 0:
      score += 8
      factors.append("paper_proof_go")
  except Exception:
    pass

  try:
    from engine.portfolio_risk import load_portfolio_state, max_portfolio_heat_pct, portfolio_risk_enabled

    if portfolio_risk_enabled():
      ps = load_portfolio_state()
      max_heat = max_portfolio_heat_pct()
      portfolio_util = ps.total_heat_pct / max_heat if max_heat > 0 else 0
      if portfolio_util >= 0.9:
        score -= 20
        factors.append(f"portfolio_heat_{ps.total_heat_pct:.1f}%_max")
      elif portfolio_util >= 0.65:
        score -= 10
        factors.append(f"portfolio_heat_{ps.total_heat_pct:.1f}%_high")
  except Exception:
    pass

  if score <= 25:
    posture = POSTURE_DEFENSIVE
  elif score <= 40:
    posture = POSTURE_CAUTIOUS
  elif score >= 62 and proof_verdict == "PROOF_GO" and cumulative_pnl > 0 and drawdown_pct < 3:
    posture = POSTURE_OPPORTUNISTIC
  else:
    posture = POSTURE_NEUTRAL

  return {
    "posture": posture,
    "score": round(score, 1),
    "factors": factors,
    "drawdown_pct": drawdown_pct,
    "halted": halted,
    "proof_verdict": proof_verdict,
    "cumulative_paper_pnl_usd": cumulative_pnl,
    "portfolio_heat_util": round(portfolio_util, 3),
    "size_cap_pct": POSTURE_SIZE_CAP[posture],
    "risk_mult": POSTURE_RISK_MULT[posture],
    "probe_only": posture == POSTURE_DEFENSIVE,
    "max_account_risk_pct": {
      POSTURE_DEFENSIVE: 0.35,
      POSTURE_CAUTIOUS: 0.55,
      POSTURE_NEUTRAL: 0.85,
      POSTURE_OPPORTUNISTIC: 1.0,
    }[posture],
  }


def tactical_risk_multiplier(posture: Optional[dict] = None) -> Tuple[float, List[str]]:
  posture = posture or assess_tactical_posture()
  mult = float(posture.get("risk_mult") or 1.0)
  label = posture.get("posture", POSTURE_NEUTRAL)
  if mult != 1.0:
    return mult, [f"tactical_{label} → ×{mult:.2f}"]
  return 1.0, []


def adjust_dca_for_posture(
  profile: str,
  reason: str,
  *,
  symbol: str,
  tf: str,
  result: dict,
  posture: Optional[dict] = None,
) -> Tuple[str, str]:
  """
  Tactical DCA bias — when defensive, prefer 30/70 on correlated 1d/1w
  (lighter first leg, heavier confirmation) even below standard corr thresholds.
  """
  posture = posture or assess_tactical_posture()
  p = posture.get("posture", POSTURE_NEUTRAL)
  if p not in (POSTURE_DEFENSIVE, POSTURE_CAUTIOUS):
    return profile, reason
  if profile != DCA_PROFILE_PYRAMID:
    return profile, reason
  corr = _corr_from_result(result)
  tactical_corr = float(os.environ.get("EW_TACTICAL_30_70_CORR", "0.55"))
  if tf in ("1d", "1w") and corr >= tactical_corr:
    from engine.execution_advanced import CORRELATION_CAP_SYMBOLS

    if symbol in CORRELATION_CAP_SYMBOLS or corr >= 0.75:
      return (
        DCA_PROFILE_30_70,
        f"tactical {p}: corr {corr:.2f} on {tf} → defensive 30/70 scale-in",
      )
  return profile, reason


def apply_tactical_to_row(row: dict, posture: Optional[dict] = None) -> dict:
  """Cap size and annotate row with tactical posture (non-blocking adjustments)."""
  posture = posture or assess_tactical_posture()
  row = dict(row)
  cap = float(posture.get("size_cap_pct") or 100)
  existing = float(row.get("gtc_size_cap_pct") or 100)
  row["gtc_size_cap_pct"] = round(min(existing, cap), 1)
  row["tactical_posture"] = posture.get("posture")
  row["tactical_score"] = posture.get("score")
  row["tactical_factors"] = "; ".join(posture.get("factors") or [])
  max_risk = float(posture.get("max_account_risk_pct") or 1.0)
  try:
    arp = float(row.get("account_risk_pct") or 0)
    if arp > max_risk:
      row["account_risk_pct"] = round(max_risk, 3)
      row["tactical_risk_capped"] = True
  except (TypeError, ValueError):
    pass
  if posture.get("probe_only") and row.get("honest_execution_tier") == "full":
    row["honest_execution_tier"] = "probe"
    row["tactical_downgrade"] = "full→probe defensive posture"
  return row


def gate_tactical(row: dict, posture: Optional[dict] = None) -> Tuple[bool, List[str]]:
  """Hard tactical blocks — account safeguard first."""
  if not tactical_safeguard_enabled():
    return True, []
  posture = posture or assess_tactical_posture()
  reasons: List[str] = []

  if posture.get("halted"):
    reasons.append("tactical_risk_halted")
    return False, reasons

  if posture.get("posture") == POSTURE_DEFENSIVE:
    tier = row.get("honest_execution_tier", "")
    if tier == "full" and os.environ.get("EW_TACTICAL_BLOCK_FULL", "1").lower() not in ("0", "false", "no"):
      reasons.append("tactical_defensive_no_full_size")
      return False, reasons
    try:
      arp = float(row.get("account_risk_pct") or 0)
      if arp > float(posture.get("max_account_risk_pct") or 0.35) + 0.01:
        reasons.append(f"tactical_defensive_risk_cap_{arp:.2f}%")
        return False, reasons
    except (TypeError, ValueError):
      pass

  return True, reasons
