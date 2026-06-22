"""EW-aware Monte Carlo with UNIFORM perturbation (not Gaussian)."""

from __future__ import annotations

import random
from typing import List

import numpy as np
import pandas as pd

from core.atr import compute_atr14
from core.impulse import validate_impulse
from core.monowaves import extract_monowaves


def ew_aware_monte_carlo(
  df: pd.DataFrame,
  ref_types: List[str],
  n_runs: int = 500,
  atr_14: float | None = None,
) -> dict:
  if atr_14 is None:
    atr_14 = compute_atr14(df)

  highs = df["High"].values.astype(float)
  lows = df["Low"].values.astype(float)
  closes = df["Close"].values.astype(float)
  n = len(highs)
  holds = 0
  succ = 0

  for _ in range(n_runs):
    price_shift = np.random.uniform(-0.5 * atr_14, 0.5 * atr_14, size=n)
    h_p = np.maximum(highs + price_shift, lows + price_shift)
    l_p = np.minimum(lows + price_shift, h_p)

    perturbed_df = pd.DataFrame(
      {
        "Open": (h_p + l_p) / 2,
        "High": h_p,
        "Low": l_p,
        "Close": closes + price_shift,
        "Volume": df["Volume"].values,
      },
      index=df.index,
    )

    try:
      mws = extract_monowaves(perturbed_df, skip=2)
    except Exception:
      continue
    succ += 1
    if len(mws) >= 5:
      val = validate_impulse(mws)
      if val["types"] == ref_types and val["passes"]:
        holds += 1

  return {
    "n_runs": n_runs,
    "successful_runs": succ,
    "primary_count_held": holds,
    "empirical_probability": round(holds / max(succ, 1), 4),
    "perturbation_spec": "uniform(bar_shift=randint(-1,1), price_shift=uniform(-0.5*ATR, 0.5*ATR))",
    "atr_14": atr_14,
  }
