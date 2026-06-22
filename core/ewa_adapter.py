"""ElliottWaveAnalyzer (drstevendev) adapter — fast impulse/correction scan."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from libs.ewa_patch import patch_ewa_imports


def prepare_ewa_df(df: pd.DataFrame) -> pd.DataFrame:
  out = df.copy()
  if "Date" not in out.columns:
    out = out.reset_index()
    out.rename(columns={out.columns[0]: "Date"}, inplace=True)
  if isinstance(out.columns, pd.MultiIndex):
    out.columns = out.columns.get_level_values(0)
  return out[["Date", "Open", "High", "Low", "Close"]]


def scan_ewa(
  df: pd.DataFrame,
  up_to: int = 6,
  max_configs: int = 150,
) -> Dict[str, Any]:
  """
  Fast scan using ElliottWaveAnalyzer GitHub library.
  Tries impulse + leading diagonal from swing low, correction from swing high.
  """
  if not patch_ewa_imports():
    return {"available": False, "error": "EWA import patch failed"}

  from models.WaveAnalyzer import WaveAnalyzer
  from models.WaveOptions import WaveOptionsGenerator3, WaveOptionsGenerator5
  from models.WavePattern import WavePattern
  from models.WaveRules import Correction, Impulse, LeadingDiagonal

  ewa_df = prepare_ewa_df(df)
  lows = ewa_df["Low"].values.astype(float)
  highs = ewa_df["High"].values.astype(float)
  n = len(ewa_df)

  wa = WaveAnalyzer(df=ewa_df, verbose=False)
  gen5 = WaveOptionsGenerator5(up_to=up_to)
  gen3 = WaveOptionsGenerator3(up_to=min(up_to, 8))

  idx_low = int(np.argmin(lows))
  idx_high = int(np.argmax(highs))
  recent_low = int(np.argmin(lows[max(0, n - 80) :])) + max(0, n - 80)

  starts_bull = list(dict.fromkeys([idx_low, recent_low]))
  starts_bear = list(dict.fromkeys([idx_high]))

  best_impulse: Optional[dict] = None
  best_diagonal: Optional[dict] = None
  best_correction: Optional[dict] = None
  configs_tried = 0

  impulse_rule = Impulse("impulse")
  diagonal_rule = LeadingDiagonal("leading diagonal")
  correction_rule = Correction("correction")

  for idx_start in starts_bull:
    for opt in gen5.options_sorted:
      if configs_tried >= max_configs:
        break
      configs_tried += 1
      try:
        waves = wa.find_impulsive_wave(idx_start=idx_start, wave_config=opt.values)
      except (ValueError, IndexError):
        continue
      if not waves:
        continue
      pattern = WavePattern(waves, wave_options=opt.values, verbose=False)
      if pattern.check_rule(impulse_rule) and best_impulse is None:
        best_impulse = {
          "rule": "impulse",
          "direction": "BULL",
          "wave_config": opt.values,
          "idx_start": idx_start,
          "idx_end": waves[-1].idx_end,
          "high": float(waves[-1].high),
        }
      if pattern.check_rule(diagonal_rule) and best_diagonal is None:
        best_diagonal = {
          "rule": "leading_diagonal",
          "direction": "BULL",
          "wave_config": opt.values,
          "idx_start": idx_start,
        }

  for idx_start in starts_bear:
    for opt in gen3.options_sorted:
      if configs_tried >= max_configs + 80:
        break
      configs_tried += 1
      try:
        waves = wa.find_corrective_wave(idx_start=idx_start, wave_config=opt.values)
      except (ValueError, IndexError):
        continue
      if not waves:
        continue
      pattern = WavePattern(waves, wave_options=opt.values, verbose=False)
      if pattern.check_rule(correction_rule) and best_correction is None:
        best_correction = {
          "rule": "correction",
          "direction": "BEAR",
          "wave_config": opt.values,
          "idx_start": idx_start,
        }

  return {
    "available": True,
    "source": "github.com/drstevendev/ElliottWaveAnalyzer",
    "configs_tried": configs_tried,
    "impulse": best_impulse,
    "leading_diagonal": best_diagonal,
    "correction": best_correction,
  }
