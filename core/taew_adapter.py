"""python-taew (DrEdwardPCB) adapter — Fibonacci wave validation consensus."""

from __future__ import annotations

from typing import Any, Dict, List

from taew import (
  wave2_fibonacci_check,
  wave3_fibonacci_check,
  wave4_fibonacci_check,
  wave5_fibonacci_check,
)


def _mw_prices(mw: dict) -> tuple[float, float]:
  return float(mw["price_start"]), float(mw["price_end"])


def scan_taew_fib(mws: List[dict]) -> Dict[str, Any]:
  """
  Run taew GitHub library fib checks on last 5 monowaves.
  Returns per-wave fib validity and aggregate score.
  """
  if len(mws) < 5:
    return {
      "available": False,
      "error": "need 5 monowaves",
      "source": "github.com/DrEdwardPCB/python-taew",
    }

  w = mws[-5:]
  types = [m["type"] for m in w]
  direction = "BULL" if types == ["Up", "Down", "Up", "Down", "Up"] else (
    "BEAR" if types == ["Down", "Up", "Down", "Up", "Down"] else "AMBIGUOUS"
  )

  w1s, w1e = _mw_prices(w[0])
  w2s, w2e = _mw_prices(w[1])
  w3s, w3e = _mw_prices(w[2])
  w4s, w4e = _mw_prices(w[3])
  w5s, w5e = _mw_prices(w[4])

  checks = {
    "wave2_fib": wave2_fibonacci_check(w2e, w1s, w1e),
    "wave3_fib": wave3_fibonacci_check(w3e, w2s, w2e),
    "wave4_fib": wave4_fibonacci_check(w4e, w3s, w3e),
    "wave5_fib": wave5_fibonacci_check(w5e, w1s, w1e, w3s, w3e, w4e),
  }
  passed = sum(1 for v in checks.values() if v)
  score = round(passed / len(checks), 3)

  return {
    "available": True,
    "source": "github.com/DrEdwardPCB/python-taew",
    "direction": direction,
    "fib_checks": checks,
    "fib_score": score,
    "valid": passed >= 3,
  }
