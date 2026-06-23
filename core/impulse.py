"""R1/R2/R3 impulse validation — strict and crypto-adaptive modes."""

from __future__ import annotations

from typing import List

# Crypto W2 may retrace up to ~123.6% of W1 before R1 is considered failed
ADAPTIVE_R1_MAX_RATIO = 1.236


def validate_impulse(mws: List[dict], mode: str = "strict") -> dict:
  if len(mws) < 5:
    return {
      "passes": False,
      "partial": False,
      "direction": "n/a",
      "violations": ["<5 monowaves"],
      "sizes": {},
      "types": [],
      "mode": mode,
    }
  types = [m["type"] for m in mws[:5]]
  if types == ["Up", "Down", "Up", "Down", "Up"]:
    direction = "BULL"
  elif types == ["Down", "Up", "Down", "Up", "Down"]:
    direction = "BEAR"
  else:
    return {
      "passes": False,
      "partial": False,
      "direction": "AMBIGUOUS",
      "violations": [f"non-impulse: {types}"],
      "sizes": {},
      "types": types,
      "mode": mode,
    }

  w = [abs(m["price_end"] - m["price_start"]) for m in mws[:5]]
  v: List[str] = []
  r1_ratio = w[1] / w[0] if w[0] > 0 else 0.0
  r1_limit = ADAPTIVE_R1_MAX_RATIO if mode == "adaptive" else 1.0
  if w[0] > 0 and r1_ratio >= r1_limit:
    v.append(f"R1(W2={r1_ratio * 100:.1f}%)")
  if w[2] == min(w[0], w[2], w[4]):
    v.append("R2")
  if direction == "BULL" and mws[3]["price_end"] < mws[0]["price_end"]:
    v.append("R3")
  if direction == "BEAR" and mws[3]["price_end"] > mws[0]["price_end"]:
    v.append("R3")

  passes = len(v) == 0

  return {
    "passes": passes,
    "partial": False,
    "direction": direction,
    "violations": v,
    "r1_ratio": round(r1_ratio, 4) if w[0] > 0 else 0.0,
    "sizes": {
      "W1": round(w[0], 2),
      "W2": round(w[1], 2),
      "W3": round(w[2], 2),
      "W4": round(w[3], 2),
      "W5": round(w[4], 2),
    },
    "types": types,
    "mode": mode,
  }
