"""Sign-symmetry: mirrored prices should flip trade directions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.fib_zone import compute_c_targets, compute_prior_decline_fibs, compute_tight_kill_zone


def _mirror_df(df: pd.DataFrame, pivot: float) -> pd.DataFrame:
  out = df.copy()
  for col in ("Open", "High", "Low", "Close"):
    out[col] = 2 * pivot - df[col].values
  # OHLC symmetry: High/Low swap under inversion
  out["High"] = np.maximum(out["Open"], out["Close"])
  out["Low"] = np.minimum(out["Open"], out["Close"])
  hi = 2 * pivot - df["Low"].values
  lo = 2 * pivot - df["High"].values
  out["High"] = np.maximum(out["High"], hi)
  out["Low"] = np.minimum(out["Low"], lo)
  return out


def _make_uptrend(n: int = 120, start: float = 50.0) -> pd.DataFrame:
  idx = pd.date_range("2025-01-01", periods=n, freq="1d", tz="UTC")
  close = start + np.linspace(0, 30, n) + np.sin(np.linspace(0, 8, n))
  df = pd.DataFrame(
    {
      "Open": close - 0.2,
      "High": close + 0.5,
      "Low": close - 0.5,
      "Close": close,
      "Volume": 1000.0,
    },
    index=idx,
  )
  return df


def test_prior_decline_fibs_sign_symmetric():
  df = _make_uptrend()
  pivot = float(df["Close"].iloc[-1])
  fib_orig = compute_prior_decline_fibs(df)
  fib_mirror = compute_prior_decline_fibs(_mirror_df(df, pivot))
  assert fib_orig and fib_mirror
  for k in fib_orig:
    expected = 2 * pivot - fib_orig[k]
    assert abs(fib_mirror[k] - expected) < 0.05, f"{k}: {fib_mirror[k]} vs {expected}"


def test_c_targets_flip_under_mirror():
  wave_a = {"start": 100.0, "end": 80.0, "type": "Down"}
  b_end = 85.0
  orig = compute_c_targets(wave_a, b_end, "bullish_reversal", "choppy")
  pivot = b_end
  wave_a_m = {"start": 2 * pivot - 80.0, "end": 2 * pivot - 100.0, "type": "Up"}
  b_m = 2 * pivot - b_end
  mir = compute_c_targets(wave_a_m, b_m, "bearish_reversal", "choppy")
  assert orig["c_direction"].startswith("up")
  assert mir["c_direction"].startswith("down")
  assert abs(mir["c_target_100"] - (2 * pivot - orig["c_target_100"])) < 0.01


def test_kill_zone_center_symmetric():
  df = _make_uptrend()
  pivot = float(df["Close"].iloc[-1])
  c = compute_c_targets({"start": 100, "end": 80, "type": "Down"}, 85, "bullish_reversal", "choppy")
  fibs = compute_prior_decline_fibs(df)
  lo, hi, _ = compute_tight_kill_zone(c["c_target_100"], c["c_target_161"], fibs, pivot)

  df_m = _mirror_df(df, pivot)
  c_m = compute_c_targets({"start": 2 * pivot - 80, "end": 2 * pivot - 100, "type": "Up"}, 2 * pivot - 85, "bearish_reversal", "choppy")
  fibs_m = compute_prior_decline_fibs(df_m)
  lo_m, hi_m, _ = compute_tight_kill_zone(c_m["c_target_100"], c_m["c_target_161"], fibs_m, pivot)
  mid = (lo + hi) / 2
  mid_m = (lo_m + hi_m) / 2
  assert abs(mid_m - (2 * pivot - mid)) < pivot * 0.02
