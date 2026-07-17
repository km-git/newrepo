"""Risk operations — drawdown circuit breaker, emergency flatten."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


STATE_PATH = Path(os.environ.get("EW_RISK_STATE", "output/execution/risk_state.json"))


def _load() -> dict:
  if not STATE_PATH.exists():
    return {"peak_equity_usd": None, "halted": False, "halt_reason": ""}
  return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _save(state: dict) -> None:
  STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
  STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def drawdown_threshold_pct() -> float:
  return float(os.environ.get("EW_DRAWDOWN_HALT_PCT", "10"))


def update_equity(equity_usd: float) -> Dict[str, Any]:
  state = _load()
  peak = state.get("peak_equity_usd")
  if peak is None or equity_usd > peak:
    state["peak_equity_usd"] = equity_usd
    peak = equity_usd
  dd = ((peak - equity_usd) / peak * 100) if peak and peak > 0 else 0.0
  state["current_equity_usd"] = equity_usd
  state["drawdown_pct"] = round(dd, 2)
  state["updated_at"] = datetime.now(timezone.utc).isoformat()
  if dd >= drawdown_threshold_pct():
    state["halted"] = True
    state["halt_reason"] = f"drawdown {dd:.1f}% >= {drawdown_threshold_pct()}%"
  _save(state)
  return state


def is_halted() -> bool:
  return bool(_load().get("halted"))


def clear_halt() -> None:
  state = _load()
  state["halted"] = False
  state["halt_reason"] = ""
  _save(state)


def emergency_flatten(dry_run: bool = True) -> Dict[str, Any]:
  """Cancel all orders — close positions when broker supports it."""
  if dry_run or os.environ.get("EW_EXECUTION_MODE", "paper") != "live":
    return {"dry_run": True, "action": "would_cancel_all"}
  from engine.broker.factory import get_broker
  broker = get_broker()
  results = []
  if hasattr(broker, "cancel_all_orders"):
    results.append(broker.cancel_all_orders())
  elif hasattr(broker, "cancel_all"):
    results.append(broker.cancel_all())
  state = _load()
  state["halted"] = True
  state["halt_reason"] = "emergency_flatten"
  _save(state)
  return {"ok": True, "results": results}
