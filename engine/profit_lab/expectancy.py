"""Expectancy by slice — drives auto-blocking in execution gates."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from engine.profit_lab.setup_returns import setups_to_returns_frame, slice_key

STATE_PATH = Path(os.environ.get("EW_EXPECTANCY_STATE", "output/profit_lab/expectancy_slices.json"))


def _state_path() -> Path:
  return Path(os.environ.get("EW_EXPECTANCY_STATE", str(STATE_PATH)))


def min_slice_samples() -> int:
  return int(os.environ.get("EW_EXPECTANCY_MIN_SAMPLES", "30"))


def min_expectancy_r() -> float:
  return float(os.environ.get("EW_EXPECTANCY_MIN_R", "0.0"))


def expectancy_enabled() -> bool:
  return os.environ.get("EW_EXPECTANCY_GATES", "1").lower() not in ("0", "false", "no")


def compute_slice_expectancy(
  df: Optional[pd.DataFrame] = None,
  *,
  dimensions: Tuple[str, ...] = ("timeframe",),
  min_n: Optional[int] = None,
) -> List[Dict[str, Any]]:
  """Expectancy (mean net_r), win rate, n per slice."""
  min_n = min_n if min_n is not None else min_slice_samples()
  df = df if df is not None else setups_to_returns_frame()
  if df.empty:
    return []

  slices: List[Dict[str, Any]] = []
  df = df.copy()
  df["_slice"] = df.apply(lambda r: slice_key(r.to_dict(), dimensions), axis=1)

  for key, grp in df.groupby("_slice"):
    n = len(grp)
    wins = int((grp["net_r"] > 0).sum())
    losses = int((grp["net_r"] < 0).sum())
    exp = float(grp["net_r"].mean()) if n else 0.0
    wr = round(wins / n, 4) if n else None
    slices.append({
      "slice": key,
      "dimensions": list(dimensions),
      "n": n,
      "wins": wins,
      "losses": losses,
      "win_rate": wr,
      "expectancy_r": round(exp, 6),
      "total_r": round(float(grp["net_r"].sum()), 4),
      "sufficient_samples": n >= min_n,
      "passes_gate": n >= min_n and exp >= min_expectancy_r(),
    })
  slices.sort(key=lambda x: (x["expectancy_r"], x["n"]), reverse=True)
  return slices


def blocked_slices_from_expectancy(
  slices: Sequence[dict],
  *,
  min_n: Optional[int] = None,
) -> Dict[str, List[str]]:
  """Return block lists keyed by dimension name (timeframe, direction, pair_tf)."""
  min_n = min_n if min_n is not None else min_slice_samples()
  blocked: Dict[str, set] = {"timeframe": set(), "direction": set(), "pair_tf": set()}
  for s in slices:
    if s.get("sufficient_samples") and not s.get("passes_gate"):
      key = str(s.get("slice") or "")
      dims = s.get("dimensions") or []
      if len(dims) == 1:
        dim = dims[0]
        if dim in blocked:
          blocked[dim].add(key)
      elif len(dims) >= 2 and dims[0] == "timeframe" and dims[1] == "direction":
        tf, direction = key.split("|", 1) if "|" in key else (key, "")
        if tf:
          blocked["timeframe"].add(tf)  # conservative: block whole TF if tf|dir fails
  return {k: sorted(v) for k, v in blocked.items()}


def build_expectancy_report(df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
  df = df if df is not None else setups_to_returns_frame()
  overall_n = len(df)
  overall_exp = float(df["net_r"].mean()) if overall_n else 0.0
  by_tf = compute_slice_expectancy(df, dimensions=("timeframe",))
  by_dir = compute_slice_expectancy(df, dimensions=("direction",))
  by_pair_tf = compute_slice_expectancy(df, dimensions=("pair_tf",))
  blocked = blocked_slices_from_expectancy(by_tf + by_dir)

  return {
    "ok": overall_n > 0,
    "overall": {
      "n": overall_n,
      "expectancy_r": round(overall_exp, 6),
      "passes_gate": overall_n >= min_slice_samples() and overall_exp >= min_expectancy_r(),
      "total_r": round(float(df["net_r"].sum()), 4) if overall_n else 0.0,
    },
    "by_timeframe": by_tf,
    "by_direction": by_dir,
    "by_pair_tf": by_pair_tf[:50],
    "blocked_slices": blocked,
    "min_samples": min_slice_samples(),
    "min_expectancy_r": min_expectancy_r(),
  }


def save_expectancy_state(report: dict) -> Path:
  path = _state_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
  return path


def load_expectancy_state() -> dict:
  path = _state_path()
  if not path.exists():
    return {}
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}


def blocked_timeframes_from_expectancy() -> set:
  if not expectancy_enabled():
    return set()
  state = load_expectancy_state()
  blocked = state.get("blocked_slices") or {}
  return set(blocked.get("timeframe") or [])


def blocked_directions_from_expectancy() -> set:
  if not expectancy_enabled():
    return set()
  state = load_expectancy_state()
  blocked = state.get("blocked_slices") or {}
  return set(blocked.get("direction") or [])
