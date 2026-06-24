"""Elliott Wave matrix — guaranteed analysis for every pair × timeframe."""

from __future__ import annotations

from typing import Dict, List

from engine.wave_detail import analyze_timeframe

DEFAULT_EW_TFS = ["1w", "1d", "4h", "1h", "15m"]


def _empty_tf(tf: str, reason: str) -> dict:
  return {
    "tf": tf,
    "status": reason,
    "structure": "no_data",
    "direction": "n/a",
    "impulse_valid": False,
    "violations": [reason],
    "monowave_count": 0,
    "waves_last5": [],
    "wave_sizes": {},
    "abc": None,
    "diagonal": None,
    "ew_complete": False,
  }


def build_ew_matrix(
  adaptive: dict,
  data: dict,
  tfs: List[str],
) -> Dict[str, dict]:
  """
  Elliott Wave analysis for EVERY requested timeframe.
  Never omits a TF — missing data gets explicit no_data entry.
  """
  matrix: Dict[str, dict] = {}
  for tf in tfs:
    if tf not in adaptive:
      matrix[tf] = _empty_tf(tf, "not_requested")
      continue
    ad = adaptive[tf]
    if ad.get("status") == "no_data" or tf not in data:
      matrix[tf] = _empty_tf(tf, "fetch_missing")
      continue
    if not ad.get("monowaves"):
      price = float(data[tf]["Close"].iloc[-1]) if len(data[tf]) else 0
      matrix[tf] = _empty_tf(tf, "insufficient_monowaves")
      matrix[tf]["current_price"] = price
      matrix[tf]["bars"] = ad.get("bars", 0)
      continue

    price = float(data[tf]["Close"].iloc[-1])
    wave = analyze_timeframe(ad["monowaves"], tf, price)
    wave["bars"] = ad.get("bars", len(data[tf]))
    wave["skip"] = ad.get("skip", 0)
    wave["status"] = "ok"
    wave["ew_complete"] = wave.get("structure") not in ("no_data", "unclassified") or bool(wave.get("abc"))
    matrix[tf] = wave

  return matrix


def ew_coverage_summary(matrix: Dict[str, dict], tfs: List[str]) -> dict:
  """Summary of EW coverage across timeframes."""
  total = len(tfs)
  ok = sum(1 for tf in tfs if matrix.get(tf, {}).get("status") == "ok")
  complete = sum(1 for tf in tfs if matrix.get(tf, {}).get("ew_complete"))
  structures = {tf: matrix.get(tf, {}).get("structure", "missing") for tf in tfs}
  return {
    "timeframes_requested": tfs,
    "timeframes_analyzed": ok,
    "timeframes_complete": complete,
    "coverage_pct": round(ok / total * 100, 1) if total else 0,
    "structures_by_tf": structures,
    "all_tfs_present": ok == total,
  }
