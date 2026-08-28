"""Per-timeframe Elliott wave structure detail."""

from __future__ import annotations

from typing import Dict, List, Optional

from core.correction import detect_abc, detect_diagonal
from core.impulse import validate_impulse


def _format_mw(mw: dict) -> dict:
  return {
    "type": mw["type"],
    "start": round(mw["price_start"], 6),
    "end": round(mw["price_end"], 6),
    "dates": f"{mw.get('date_start', '')} → {mw.get('date_end', '')}",
  }


def analyze_timeframe(mws: List[dict], tf: str, current_price: float) -> dict:
  """Full wave readout for one timeframe."""
  if not mws:
    return {"tf": tf, "status": "no_data", "structure": "no_data", "monowave_count": 0}

  best_impulse: Optional[dict] = None
  best_start = -1
  for start in range(len(mws) - 4):
    val = validate_impulse(mws[start : start + 5])
    if val["passes"]:
      best_impulse = val
      best_start = start
      break
    if best_impulse is None and val["direction"] not in ("AMBIGUOUS", "n/a"):
      best_impulse = val
      best_start = start

  last5_val = validate_impulse(mws[-5:]) if len(mws) >= 5 else None
  abc = detect_abc(mws)
  diagonal = detect_diagonal(mws)

  impulse = best_impulse or last5_val
  waves_5 = mws[best_start : best_start + 5] if best_start >= 0 and len(mws) >= best_start + 5 else mws[-5:]

  structure = "unclassified"
  if impulse and impulse.get("passes"):
    structure = f"{impulse['direction'].lower()}_impulse_5"
  elif abc:
    structure = "abc_correction"
  elif diagonal:
    structure = "ending_diagonal"
  elif impulse and impulse.get("violations"):
    structure = f"invalid_impulse ({impulse['violations'][0]})"

  return {
    "tf": tf,
    "monowave_count": len(mws),
    "structure": structure,
    "direction": impulse.get("direction", "n/a") if impulse else "n/a",
    "impulse_valid": bool(impulse and impulse.get("passes")),
    "violations": impulse.get("violations", []) if impulse else [],
    "wave_sizes": impulse.get("sizes", {}) if impulse else {},
    "waves_last5": [_format_mw(m) for m in waves_5] if len(waves_5) >= 5 else [_format_mw(m) for m in mws[-3:]],
    "abc": {
      "wave_B_retrace_pct": abc["wave_B"]["retrace_pct"],
      "wave_C_progress_pct": abc["wave_C"]["progress_pct"],
      "c_target_100": round(abc["wave_C"]["target_100"], 4),
      "c_target_161": round(abc["wave_C"]["target_161"], 4),
    } if abc else None,
    "diagonal": diagonal.get("direction") if diagonal else None,
    "current_price": round(current_price, 6),
  }


def analyze_all_timeframes(
  adaptive: Dict[str, dict],
  data: Dict,
  tfs: List[str],
) -> Dict[str, dict]:
  out = {}
  for tf in tfs:
    if tf not in adaptive or tf not in data:
      continue
    price = float(data[tf]["Close"].iloc[-1])
    out[tf] = analyze_timeframe(adaptive[tf]["monowaves"], tf, price)
  return out
