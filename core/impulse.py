"""Strict R1/R2/R3 impulse validation."""

from __future__ import annotations

from typing import List


def validate_impulse(mws: List[dict]) -> dict:
  if len(mws) < 5:
    return {
      "passes": False,
      "direction": "n/a",
      "violations": ["<5 monowaves"],
      "sizes": {},
      "types": [],
    }
  types = [m["type"] for m in mws[:5]]
  if types == ["Up", "Down", "Up", "Down", "Up"]:
    direction = "BULL"
  elif types == ["Down", "Up", "Down", "Up", "Down"]:
    direction = "BEAR"
  else:
    return {
      "passes": False,
      "direction": "AMBIGUOUS",
      "violations": [f"non-impulse: {types}"],
      "sizes": {},
      "types": types,
    }

  w = [abs(m["price_end"] - m["price_start"]) for m in mws[:5]]
  v: List[str] = []
  if w[0] > 0 and w[1] / w[0] >= 1.0:
    v.append(f"R1(W2={w[1] / w[0] * 100:.1f}%)")
  if w[2] == min(w[0], w[2], w[4]):
    v.append("R2")
  if direction == "BULL" and mws[3]["price_end"] < mws[0]["price_end"]:
    v.append("R3")
  if direction == "BEAR" and mws[3]["price_end"] > mws[0]["price_end"]:
    v.append("R3")

  return {
    "passes": len(v) == 0,
    "direction": direction,
    "violations": v,
    "sizes": {
      "W1": round(w[0], 2),
      "W2": round(w[1], 2),
      "W3": round(w[2], 2),
      "W4": round(w[3], 2),
      "W5": round(w[4], 2),
    },
    "types": types,
  }
