"""Local paper ledger — simulated fills when kraken-cli unavailable."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def ledger_path() -> Path:
  raw = os.environ.get("EW_PAPER_LEDGER", "output/execution/paper_ledger.json")
  return Path(raw)


def _utc() -> str:
  return datetime.now(timezone.utc).isoformat()


def load_ledger() -> dict:
  path = ledger_path()
  if not path.exists():
    return {
      "mode": "paper",
      "balance_usd": float(os.environ.get("EW_PAPER_BALANCE", "10000")),
      "positions": {},
      "orders": [],
      "fills": [],
    }
  return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(state: dict) -> None:
  path = ledger_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def place_paper_order(
  *,
  symbol: str,
  side: str,
  order_type: str,
  amount: float,
  price: Optional[float] = None,
  client_id: str = "",
  meta: Optional[dict] = None,
) -> Dict[str, Any]:
  state = load_ledger()
  oid = client_id or f"paper-{len(state['orders'])+1}"
  notional = amount * (price or 0)
  order = {
    "id": oid,
    "symbol": symbol,
    "side": side,
    "type": order_type,
    "amount": amount,
    "price": price,
    "status": "open" if order_type == "limit" else "filled",
    "created_at": _utc(),
    "meta": meta or {},
  }
  state["orders"].append(order)
  if order["status"] == "filled" and price:
    fill = {
      "order_id": oid,
      "symbol": symbol,
      "side": side,
      "amount": amount,
      "price": price,
      "notional_usd": notional,
      "filled_at": _utc(),
    }
    state["fills"].append(fill)
    pos = state["positions"].get(symbol, {"amount": 0.0, "avg_price": 0.0})
    signed = amount if side == "buy" else -amount
    new_amt = pos["amount"] + signed
    if abs(new_amt) < 1e-12:
      state["positions"].pop(symbol, None)
    else:
      pos["amount"] = new_amt
      pos["avg_price"] = price
      state["positions"][symbol] = pos
    state["balance_usd"] = round(state["balance_usd"] - (notional if side == "buy" else -notional), 2)
  save_ledger(state)
  return {"ok": True, "order": order, "mode": "paper"}


def paper_status() -> dict:
  return load_ledger()


def cancel_paper_order(order_id: str) -> dict:
  state = load_ledger()
  for o in state["orders"]:
    if o["id"] == order_id and o["status"] == "open":
      o["status"] = "cancelled"
      o["cancelled_at"] = _utc()
      save_ledger(state)
      return {"ok": True, "order_id": order_id}
  return {"ok": False, "error": "not_found"}


def list_paper_orders(status: str = "") -> List[dict]:
  orders = load_ledger().get("orders", [])
  if status:
    return [o for o in orders if o.get("status") == status]
  return orders
