"""ABC correction and ending diagonal detection."""

from __future__ import annotations

from typing import List, Optional


def detect_abc(mws: List[dict]) -> Optional[dict]:
  if len(mws) < 3:
    return None
  abc = mws[-3:]
  types = [m["type"] for m in abc]
  if not (types[0] == types[2] and types[1] != types[0]):
    return None

  a_mag = abs(abc[0]["price_end"] - abc[0]["price_start"])
  b_mag = abs(abc[1]["price_end"] - abc[1]["price_start"])
  c_mag = abs(abc[2]["price_end"] - abc[2]["price_start"])
  if a_mag == 0:
    return None

  b_retrace = b_mag / a_mag
  c_progress = c_mag / a_mag
  if not (0.382 <= b_retrace <= 1.0):
    return None
  if c_progress > 1.618:
    return None

  c_dir = abc[2]["type"]
  if c_dir == "Up":
    tgt_100 = abc[1]["price_end"] + a_mag
    tgt_161 = abc[1]["price_end"] + a_mag * 1.618
  else:
    tgt_100 = abc[1]["price_end"] - a_mag
    tgt_161 = abc[1]["price_end"] - a_mag * 1.618

  return {
    "structure": "ABC_correction",
    "wave_A": {
      "type": abc[0]["type"],
      "magnitude": a_mag,
      "start": abc[0]["price_start"],
      "end": abc[0]["price_end"],
    },
    "wave_B": {
      "type": abc[1]["type"],
      "retrace_pct": round(b_retrace * 100, 2),
      "in_range": True,
    },
    "wave_C": {
      "type": abc[2]["type"],
      "progress_pct": round(c_progress * 100, 2),
      "target_100": tgt_100,
      "target_161": tgt_161,
      "in_progress": c_progress < 0.95,
    },
    "direction_C_current": c_dir.lower(),
    "reversal_after_C": "up" if c_dir == "Down" else "down",
  }


def detect_diagonal(mws: List[dict]) -> Optional[dict]:
  if len(mws) < 5:
    return None
  last5 = mws[-5:]
  types = [m["type"] for m in last5]

  if types[0] == "Up" and types[2] == "Up" and types[4] == "Up":
    direction = "bullish_ending"
  elif types[0] == "Down" and types[2] == "Down" and types[4] == "Down":
    direction = "bearish_ending"
  else:
    return None

  magnitudes = [abs(m["price_end"] - m["price_start"]) for m in last5]
  if not (magnitudes[0] > magnitudes[2] > magnitudes[4]):
    return None

  if direction == "bullish_ending":
    if last5[3]["price_end"] > last5[0]["price_end"]:
      return None
  else:
    if last5[3]["price_end"] < last5[0]["price_end"]:
      return None

  return {
    "structure": "ending_diagonal",
    "direction": "reversal_up" if direction == "bearish_ending" else "reversal_down",
    "magnitudes": [round(m, 2) for m in magnitudes],
    "wedge_confirmed": True,
    "R3_relaxed": True,
  }
