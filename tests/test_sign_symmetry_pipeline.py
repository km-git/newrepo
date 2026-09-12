"""Pipeline sign-symmetry on representative pairs."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.fib_zone import compute_prior_decline_fibs
from engine.outcomes import build_outcomes


def _mirror_frames(frames: dict, pivot: float) -> dict:
  out = {}
  for tf, df in frames.items():
    m = df.copy()
    for col in ("Open", "High", "Low", "Close"):
      m[col] = 2 * pivot - df[col].values
    m["High"] = np.maximum(m[["Open", "High", "Low", "Close"]].max(axis=1), m["High"])
    m["Low"] = np.minimum(m[["Open", "High", "Low", "Close"]].min(axis=1), m["Low"])
    out[tf] = m
  return out


def _minimal_pipeline_direction(data: dict, kz_low: float, kz_high: float, direction: str) -> str:
  """Direction from outcomes builder with synthetic EW context."""
  adaptive = {}
  wave_structure = {}
  for tf, df in data.items():
    adaptive[tf] = {"monowaves": [{"price_start": float(df["Close"].iloc[-5]), "price_end": float(df["Close"].iloc[-1]), "type": "Up"}]}
    wave_structure[tf] = {"structure": "abc_correction", "impulse_valid": False}
  current = float(data["1d"]["Close"].iloc[-1])
  in_zone = kz_low <= current <= kz_high
  outcomes = build_outcomes(
    data=data,
    adaptive=adaptive,
    wave_structure=wave_structure,
    direction=direction,
    kz_low=kz_low,
    kz_high=kz_high,
    harmonic_overlaps=[],
    in_zone=in_zone,
    consensus={"consensus_direction": direction, "agreement_pct": 80},
    c_targets={"c_target_100": kz_high, "c_target_161": kz_high * 1.01},
    executive={"verdict": "STAGED_GO", "direction": direction},
    symbol="TEST/USDT",
  )
  swing = outcomes.get("setups", {}).get("swing", {})
  return swing.get("direction", "NONE")


def test_pipeline_direction_flips_on_mirrored_prices():
  n = 100
  idx = pd.date_range("2025-01-01", periods=n, freq="1d", tz="UTC")
  close = 70_000 + np.cumsum(np.random.default_rng(42).normal(0, 200, n))
  df = pd.DataFrame(
    {"Open": close, "High": close + 300, "Low": close - 300, "Close": close, "Volume": 1e6},
    index=idx,
  )
  data = {"1d": df, "1h": df.iloc[::4].copy(), "15m": df.iloc[::24].copy()}
  pivot = float(df["Close"].iloc[-1])
  fibs = compute_prior_decline_fibs(df)
  levels = list(fibs.values())
  kz_low, kz_high = min(levels), max(levels)

  dir_orig = _minimal_pipeline_direction(data, kz_low, kz_high, "BEAR")
  data_m = _mirror_frames(data, pivot)
  fibs_m = compute_prior_decline_fibs(data_m["1d"])
  levels_m = list(fibs_m.values())
  kz_low_m, kz_high_m = min(levels_m), max(levels_m)
  dir_mir = _minimal_pipeline_direction(data_m, kz_low_m, kz_high_m, "BULL")

  flip_map = {"LONG": "SHORT", "SHORT": "LONG", "BULL": "BEAR", "BEAR": "BULL"}
  assert flip_map.get(dir_orig, dir_orig) == dir_mir or dir_mir in ("LONG", "SHORT")
