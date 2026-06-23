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

  adaptive_tf = tf in ("15m", "1h", "4h")
  best_impulse: Optional[dict] = None
  best_strict_at: Optional[dict] = None
  best_adaptive_at: Optional[dict] = None
  best_start = -1
  best_rank = 99

  def _rank(val: dict) -> int:
    if val.get("passes"):
      return 0
    return 1 + len(val.get("violations", []))

  for start in range(len(mws) - 4):
    chunk = mws[start : start + 5]
    val_strict = validate_impulse(chunk, mode="strict")
    val_adaptive = validate_impulse(chunk, mode="adaptive") if adaptive_tf else val_strict
    val = val_adaptive if _rank(val_adaptive) <= _rank(val_strict) else val_strict
    rank = _rank(val)
    if rank < best_rank:
      best_impulse = val
      best_strict_at = val_strict
      best_adaptive_at = val_adaptive
      best_start = start
      best_rank = rank
      if rank == 0:
        break

  last5_val = validate_impulse(mws[-5:], mode="adaptive" if adaptive_tf else "strict") if len(mws) >= 5 else None
  abc = detect_abc(mws)
  diagonal = detect_diagonal(mws)

  impulse = best_impulse or last5_val
  if impulse is last5_val and len(mws) >= 5:
    best_strict_at = validate_impulse(mws[-5:], mode="strict")
    best_adaptive_at = last5_val if adaptive_tf else best_strict_at

  waves_5 = mws[best_start : best_start + 5] if best_start >= 0 and len(mws) >= best_start + 5 else mws[-5:]

  strict_ok = bool(best_strict_at and best_strict_at.get("passes"))
  adaptive_ok = bool(best_adaptive_at and best_adaptive_at.get("passes"))
  impulse_partial = adaptive_ok and not strict_ok

  structure = "unclassified"
  if strict_ok:
    structure = f"{impulse['direction'].lower()}_impulse_5"
  elif impulse_partial:
    structure = f"{impulse['direction'].lower()}_impulse_partial"
  elif abc:
    structure = "abc_correction"
  elif diagonal:
    structure = "ending_diagonal"
  elif impulse and impulse.get("violations"):
    structure = f"invalid_impulse ({impulse['violations'][0]})"

  impulse_valid = strict_ok or impulse_partial

  return {
    "tf": tf,
    "monowave_count": len(mws),
    "structure": structure,
    "direction": impulse.get("direction", "n/a") if impulse else "n/a",
    "impulse_valid": impulse_valid,
    "impulse_partial": impulse_partial,
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
