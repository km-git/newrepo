"""Smart dynamic risk stack — always pyramid DCA, dynamic SL, dynamic targets."""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from core.risk import DCA_PROFILE_PYRAMID, DCA_SPLITS, build_dca_ladder

SMART_DCA_SPLITS: List[int] = DCA_SPLITS  # 10, 20, 30, 40
SMART_STOP_ARCH = "smart_dynamic_sl"
SMART_TARGET_ARCH = "smart_dynamic_tp"


def alt_dca_profiles_allowed() -> bool:
  """Opt-in only: EW_ALLOW_ALT_DCA_PROFILES=1 enables 10/90 or 30/70 two-layer."""
  return os.environ.get("EW_ALLOW_ALT_DCA_PROFILES", "").lower() in ("1", "true", "yes")


def resolve_dca_profile(symbol: str, tf: str, result: dict, ctx) -> Tuple[str, str]:
  """Default: asymmetric pyramid 10/20/30/40 on every pair×TF."""
  if alt_dca_profiles_allowed():
    from engine.execution_advanced import select_dca_profile_legacy

    return select_dca_profile_legacy(symbol, tf, result, ctx)
  return DCA_PROFILE_PYRAMID, "smart asymmetric pyramid 10/20/30/40 (always on)"


def build_smart_dca_ladder(
  direction: str,
  anchor: float,
  atr: float,
  zone_low: float,
  zone_high: float,
  fib_levels: Optional[List[float]] = None,
  *,
  harmonic_prz: Optional[Tuple[float, float]] = None,
  gtc: bool = True,
  current: Optional[float] = None,
) -> List[dict]:
  """4-leg pyramid DCA — the only default export profile."""
  return build_dca_ladder(
    direction,
    anchor,
    atr,
    zone_low,
    zone_high,
    fib_levels,
    harmonic_prz=harmonic_prz,
    gtc=gtc,
    profile=DCA_PROFILE_PYRAMID,
    current=current,
  )
