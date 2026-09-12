#!/usr/bin/env python3
"""Sign-symmetry audit: mirrored OHLCV should flip swing directions."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.adaptive import adaptive_pipeline
from fetchers import fetch

TFS = ["1w", "1d", "4h", "1h", "15m"]


def _mirror_df(df: pd.DataFrame, pivot: float) -> pd.DataFrame:
  m = df.copy()
  for col in ("Open", "High", "Low", "Close"):
    m[col] = 2 * pivot - df[col].values
  m["High"] = np.maximum(m[["Open", "Close"]].max(axis=1), 2 * pivot - df["Low"].values)
  m["Low"] = np.minimum(m[["Open", "Close"]].min(axis=1), 2 * pivot - df["High"].values)
  return m


def _flip(d: str) -> str:
  d = (d or "").upper()
  if d in ("LONG", "BULL"):
    return "SHORT"
  if d in ("SHORT", "BEAR"):
    return "LONG"
  return d


def audit_symbol(sym: str) -> dict:
  os.environ.setdefault("EW_FETCH_QUIET", "1")
  os.environ.setdefault("EW_GATEWAY_QUIET", "1")
  data = fetch(sym, TFS, True)
  if "1d" not in data:
    return {"symbol": sym, "error": "no 1d data", "symmetric": False}
  pivot = float(data["1d"]["Close"].iloc[-1])
  r1 = adaptive_pipeline(sym, TFS, True, data_override=data)
  d1 = (r1.get("step8_outcomes") or {}).get("setups", {}).get("swing", {}).get("direction")

  data_m = {tf: _mirror_df(data[tf], pivot) for tf in data}
  r2 = adaptive_pipeline(sym, TFS, True, data_override=data_m)
  d2 = (r2.get("step8_outcomes") or {}).get("setups", {}).get("swing", {}).get("direction")

  ok = d1 and d2 and _flip(d1) == d2
  return {"symbol": sym, "orig": d1, "mirrored": d2, "symmetric": bool(ok)}


def main() -> int:
  analysis = sorted(ROOT.glob("output/top50_analysis_*.json"))
  if not analysis:
    print(json.dumps({"error": "no batch analysis found"}, indent=2))
    return 1
  rows = json.loads(analysis[-1].read_text())
  symbols = [r["symbol"] for r in rows if r.get("symbol")]
  results = []
  for sym in symbols:
    try:
      results.append(audit_symbol(sym))
    except Exception as exc:
      results.append({"symbol": sym, "error": str(exc), "symmetric": False})

  asym = [r for r in results if not r.get("symmetric")]
  out = {
    "pairs_tested": len(results),
    "symmetric": len(results) - len(asym),
    "asymmetric": len(asym),
    "asymmetry_pct": round(100 * len(asym) / max(1, len(results)), 1),
    "failures": asym[:20],
  }
  print(json.dumps(out, indent=2))
  return 0 if not asym else 1


if __name__ == "__main__":
  raise SystemExit(main())
