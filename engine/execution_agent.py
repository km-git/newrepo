"""Execution agent — gates → router → broker with data hub intel."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.broker.factory import broker_kind, execution_mode, get_broker
from engine.execution_gates import gate_row
from engine.execution_router import filter_executable_rows, row_to_orders
from engine.fill_tracker import record_live_fill
from engine.risk_ops import emergency_flatten, is_halted, update_equity
from gateway.data_hub import live_market_state


def load_export_csv(path: str = "") -> List[dict]:
  p = Path(path or os.environ.get("EW_LIMIT_ORDERS_CSV", "output/latest_limit_orders_all_tf.csv"))
  if not p.exists():
    return []
  with p.open(newline="", encoding="utf-8") as f:
    return list(csv.DictReader(f))


def _submit_order(broker, order: dict, dry_run: bool) -> Dict[str, Any]:
  if dry_run:
    return {"dry_run": True, "order": order}
  kind = broker_kind()
  if kind == "paper_ledger":
    return broker.place_paper_order(
      symbol=order["symbol"],
      side=order["side"],
      order_type="limit",
      amount=order["amount"],
      price=order.get("price"),
      client_id=order.get("client_id", ""),
      meta=order.get("meta"),
    )
  if kind == "kraken_cli" and order.get("type") == "limit":
    pair = order.get("kraken_pair", "")
    fn = broker.paper_buy if order["side"] == "buy" else broker.paper_sell
    if execution_mode() == "live":
      fn = broker.order_buy if order["side"] == "buy" else broker.order_sell
    return fn(pair, order["amount"], price=order["price"], validate=False)
  if order.get("type") == "limit":
    return broker.place_limit_order(
      symbol=order["symbol"],
      side=order["side"],
      amount=order["amount"],
      price=order["price"],
      client_id=order.get("client_id", ""),
    )
  if order.get("type") == "stop_loss_limit":
    return broker.place_stop_loss_limit(
      symbol=order["symbol"],
      side=order["side"],
      amount=order["amount"],
      trigger_price=order["trigger_price"],
      limit_price=order["price"],
    )
  return {"skipped": True, "reason": f"unsupported_type={order.get('type')}"}


def execute_rows(
  rows: List[dict],
  *,
  dry_run: Optional[bool] = None,
  max_orders: int = 0,
) -> Dict[str, Any]:
  """
  Execute executable export rows through broker.
  Default dry_run=True unless EW_EXECUTION_MODE=live and EW_EXECUTE_CONFIRM=1.
  """
  dry = dry_run
  if dry is None:
    dry = execution_mode() != "live" or os.environ.get("EW_EXECUTE_CONFIRM", "0") != "1"

  if is_halted():
    return {"ok": False, "error": "risk_halt_active", "dry_run": dry}

  broker = get_broker()
  executable = filter_executable_rows(rows)
  submitted: List[dict] = []
  blocked: List[dict] = []
  order_count = 0

  for row in executable:
    intel = live_market_state(row["symbol"], start_ws=True)
    allowed, reasons = gate_row(row, intel=intel)
    if not allowed:
      blocked.append({"symbol": row.get("symbol"), "tf": row.get("timeframe"), "reasons": reasons})
      continue
    for order in row_to_orders(row):
      if max_orders and order_count >= max_orders:
        break
      try:
        result = _submit_order(broker, order, dry)
        submitted.append({"order": order, "result": result})
        if not dry and result.get("ok"):
          record_live_fill({
            "client_id": order.get("client_id"),
            "symbol": order["symbol"],
            "side": order["side"],
            "amount": order["amount"],
            "price": order.get("price"),
            "broker": broker_kind(),
          })
        order_count += 1
      except Exception as e:
        submitted.append({"order": order, "error": str(e)})
    if max_orders and order_count >= max_orders:
      break

  eq = float(os.environ.get("ACCOUNT_EQUITY", "10000"))
  risk = update_equity(eq)

  return {
    "ok": True,
    "dry_run": dry,
    "mode": execution_mode(),
    "broker": broker_kind(),
    "executable_rows": len(executable),
    "orders_submitted": len(submitted),
    "blocked": blocked,
    "submitted": submitted,
    "risk": risk,
  }


def execute_from_csv(path: str = "", **kwargs) -> Dict[str, Any]:
  rows = load_export_csv(path)
  return execute_rows(rows, **kwargs)


def execution_status() -> Dict[str, Any]:
  from engine.broker.paper_ledger import paper_status
  from gateway.proxy_pool import get_proxy_pool
  from gateway.ws_hub import get_ws_hub

  status: Dict[str, Any] = {
    "mode": execution_mode(),
    "broker": broker_kind(),
    "halted": is_halted(),
    "proxy": get_proxy_pool().stats(),
    "ws_snapshots": len(get_ws_hub().all_snapshots()),
  }
  if broker_kind() == "paper_ledger":
    status["paper"] = paper_status()
  return status
