"""Calibration-weighted live execution — sizing, MSB demotion, OOS gates."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from engine.indicator_calibration import (
  apply_extra_calibration_tokens,
  build_hybrid_weights,
  load_calibration,
)
from engine.readiness import resolve_execution_status

# Tokens with negative lift in SMC ledger — penalize at live time
ANTI_PREDICTIVE_TOKENS = frozenset({
  "MSB z-score pass",
})

WEAK_MSb_TOKEN = "MSB z-score weak"

SMC_COHORT_SIZE = {"full": 0.50, "probe": 0.25}


def token_confidence_multiplier(active_tokens: List[str], calibration: Optional[dict] = None) -> float:
  """Scale size by calibration token weights; penalize anti-predictive tokens."""
  if not active_tokens:
    return 1.0
  cal = calibration or load_calibration()
  mult = 1.0
  if cal and cal.get("available"):
    weights, blocked, _ = build_hybrid_weights(cal)
    total = 0
    n = 0
    for tok in active_tokens:
      if tok in blocked or tok in ANTI_PREDICTIVE_TOKENS:
        mult *= 0.75
        continue
      w = weights.get(tok, 0)
      if w > 0:
        total += w
        n += 1
    if n:
      mult *= min(1.25, 0.85 + total / (n * 40))
  for tok in active_tokens:
    if tok in ANTI_PREDICTIVE_TOKENS:
      mult *= 0.6
    elif tok == WEAK_MSb_TOKEN:
      mult *= 0.85
  return round(max(0.25, min(1.25, mult)), 3)


def apply_msb_pass_demotion(setup: dict, msb: Optional[dict] = None) -> dict:
  """
  Runtime MSB hard block: MSB z-score pass is anti-predictive in ledger (~11% WR).
  Clears entry_signal / demotes executable setups when pass fires.
  """
  from core.msb_zscore import msb_blocks_entry

  setup = dict(setup)
  msb = msb or {}
  msb_pass = bool(msb.get("pass")) if msb.get("status") == "ok" else False
  blocked = msb_blocks_entry(msb)

  if blocked and (setup.get("entry_signal") or setup.get("entry_probe")):
    setup["entry_signal"] = False
    setup["entry_probe"] = False
    if setup.get("status") == "executable":
      setup["status"] = "monitor"
      setup["execution_tier"] = "none"
    setup["msb_gate"] = "blocked_pass"
    setup["honest_reason"] = (
      setup.get("honest_reason", "") + " · MSB z-score pass blocked (anti-predictive)"
    ).strip()

  setup["msb_pass"] = msb_pass
  setup["msb_z"] = msb.get("z")
  return setup


def calibrated_size_pct(
  setup: dict,
  base_size_pct: float,
  calibration: Optional[dict] = None,
) -> Tuple[float, List[str]]:
  """Final position size % after tier cohort sizing × calibration multiplier."""
  notes: List[str] = []
  tier = setup.get("execution_tier", "none")
  cohort_base = SMC_COHORT_SIZE.get(tier, 0.35 if tier == "probe" else 0.5)
  if setup.get("style") == "smc":
    size = base_size_pct * cohort_base
    notes.append(f"smc_cohort_{tier}={cohort_base:.0%}")
  else:
    size = base_size_pct

  tokens = setup.get("indicators", {}).get("active_tokens") or []
  if not tokens and setup.get("indicator_signals"):
    tokens = setup["indicator_signals"]
  mult = token_confidence_multiplier(tokens, calibration)
  if mult != 1.0:
    notes.append(f"cal_mult={mult}")
  size = round(min(100, max(5, size * mult)), 1)
  return size, notes


def resolve_live_status(
  setup: dict,
  style: str = "smc",
  executive_verdict: str = "",
  msb: Optional[dict] = None,
) -> dict:
  """Re-resolve execution status with OOS + MSB demotion for live/monitor upgrades."""
  setup = apply_msb_pass_demotion(setup, msb)

  if style != "smc":
    return setup

  wave_stub = {
    "structure": setup.get("structure_event") or "smc",
    "impulse_valid": setup.get("entry_signal"),
    "impulse_partial": (setup.get("confluence_count") or 0) >= 2,
  }
  indicators = setup.get("indicators") or {
    "score": setup.get("readiness_score", 0),
    "threshold": 45,
    "aligned": (setup.get("readiness_score") or 0) >= 45,
    "signals": setup.get("indicator_signals", []),
    "stop_dist_pct": (setup.get("stop_loss") or {}).get("distance_pct"),
  }
  targets = setup.get("targets") or []
  rr = targets[1]["rr"] if len(targets) > 1 else 0
  entry = setup.get("entry") or {}
  zone = entry.get("zone") or [0, 0]
  in_zone = bool(entry.get("anchor")) and zone[0] and zone[1] and zone[0] <= entry["anchor"] <= zone[1]

  status, tier, reason = resolve_execution_status(
    style="day_trade",
    direction=setup.get("direction", "LONG"),
    wave=wave_stub,
    in_zone=in_zone or bool(setup.get("active_ob") or setup.get("active_fvg")),
    zone_dist_pct=setup.get("zone_dist_pct", 99),
    impulse_valid=setup.get("entry_signal", False),
    consensus_dir=setup.get("consensus_direction", "NEUTRAL"),
    rr=rr,
    min_rr=1.5,
    harmonic_near=False,
    indicator=indicators,
    executive_verdict=executive_verdict or "STAGED_GO",
    impulse_partial=(setup.get("confluence_count") or 0) >= 2,
    smc_valid=setup.get("entry_signal") or setup.get("entry_probe") or setup.get("entry_grade") in ("A", "B"),
    smc_partial=(setup.get("confluence_count") or 0) >= 1,
    smc_aligned=True,
    smc_structure=setup.get("structure_event", ""),
    oos_win_rate=setup.get("oos_win_rate"),
    oos_trades=int(setup.get("oos_trades") or 0),
  )

  if setup.get("msb_gate") in ("demoted_weak", "blocked_pass"):
    status, tier = "monitor", "none"

  setup["status"] = status
  setup["execution_tier"] = tier
  setup["honest_reason"] = reason
  return setup
