"""Map limit-order export rows → broker order plans."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from engine.broker.symbol_map import client_order_id, for_kraken_cli
from engine.execution_advanced import compute_leg_dollars, resolve_account_equity


def _parse_dca_legs(raw: Any) -> List[dict]:
  if not raw:
    return []
  if isinstance(raw, list):
    return [leg for leg in raw if isinstance(leg, dict)]
  if isinstance(raw, str):
    try:
      parsed = json.loads(raw)
      if isinstance(parsed, list):
        return [leg for leg in parsed if isinstance(leg, dict)]
    except (json.JSONDecodeError, TypeError):
      return []
  return []


def _leg_notional_usd(row: dict, leg: dict, leg_n: int) -> float:
  """Resolve USD notional for one DCA leg from export columns or risk formula."""
  usd_key = f"leg{leg_n}_usd"
  usd = float(row.get(usd_key) or 0)
  if usd > 0:
    return usd

  pos_usd = float(row.get("position_notional_usd") or 0)
  if pos_usd > 0:
    pct = float(leg.get("size_pct") or 0) / 100.0
    return pos_usd * pct

  wae = float(row.get("wae") or 0)
  stop = float(row.get("stop_loss") or 0)
  risk_pct = float(row.get("account_risk_pct") or 0)
  if wae <= 0 or stop <= 0 or risk_pct <= 0:
    return 0.0

  legs = _parse_dca_legs(row.get("dca_legs"))
  if not legs:
    return 0.0
  equity = float(row.get("account_equity") or resolve_account_equity())
  sizing = compute_leg_dollars(
    equity,
    legs,
    wae,
    stop,
    risk_pct,
    float(row.get("gtc_size_cap_pct") or 100),
    macro_long_boost_pct=float(row.get("macro_long_boost_pct") or 0),
  )
  return float(sizing.get("leg_usd", {}).get(usd_key, 0))


def row_to_orders(row: dict) -> List[Dict[str, Any]]:
  """Convert one export row to a list of limit leg orders + optional stop/TP."""
  if row.get("status") == "error":
    return []
  orders: List[Dict[str, Any]] = []
  symbol = row.get("symbol", "")
  direction = row.get("direction", "LONG")
  side = "buy" if direction == "LONG" else "sell"
  tf = row.get("timeframe", "")
  cap = float(row.get("gtc_size_cap_pct") or 100) / 100.0
  honest = row.get("honest_execution_tier", "")
  if honest == "probe":
    cap = min(cap, 0.5)

  legs = _parse_dca_legs(row.get("dca_legs"))
  for leg in legs:
    leg_n = int(leg.get("leg") or 1)
    price = float(leg.get("price") or 0)
    if price <= 0:
      continue
    usd = _leg_notional_usd(row, leg, leg_n)
    if usd <= 0 and cap < 1.0:
      # Legacy rows: position_notional may omit tier cap — apply probe cap once.
      pos_usd = float(row.get("position_notional_usd") or 0)
      if pos_usd > 0:
        pct = float(leg.get("size_pct") or 0) / 100.0
        usd = pos_usd * pct * cap
    amount = usd / price if price else 0
    if amount <= 0:
      continue
    cid = client_order_id(symbol, tf, leg_n)
    orders.append({
      "symbol": symbol,
      "side": side,
      "type": "limit",
      "amount": round(amount, 8),
      "price": price,
      "client_id": cid,
      "leg": leg_n,
      "time_in_force": "GTC",
      "kraken_pair": for_kraken_cli(symbol),
      "notional_usd": round(usd, 2),
      "meta": {
        "timeframe": tf,
        "style": row.get("style"),
        "gtc_tier": row.get("gtc_tier"),
        "honest_execution_tier": honest,
      },
    })

  stop = float(row.get("stop_loss") or 0)
  if stop > 0 and orders:
    total_amt = sum(o["amount"] for o in orders)
    stop_side = "sell" if side == "buy" else "buy"
    orders.append({
      "symbol": symbol,
      "side": stop_side,
      "type": "stop_loss_limit",
      "amount": round(total_amt, 8),
      "trigger_price": stop,
      "price": stop * (0.999 if stop_side == "sell" else 1.001),
      "client_id": client_order_id(symbol, tf, 9, "-sl"),
      "meta": {"role": "stop_loss"},
    })

  for i, tp_key in enumerate(("tp1", "tp2", "tp3"), start=1):
    tp = float(row.get(tp_key) or 0)
    exit_key = f"tp{i}_exit_pct"
    exit_pct = float(row.get(exit_key) or 0)
    if tp <= 0 or exit_pct <= 0 or not orders:
      continue
    total_amt = sum(o["amount"] for o in orders if o.get("type") == "limit")
    tp_amt = total_amt * exit_pct / 100.0
    tp_side = "sell" if side == "buy" else "buy"
    orders.append({
      "symbol": symbol,
      "side": tp_side,
      "type": "take_profit_limit",
      "amount": round(tp_amt, 8),
      "price": tp,
      "client_id": client_order_id(symbol, tf, 9, f"-tp{i}"),
      "meta": {"role": f"tp{i}", "exit_pct": exit_pct},
    })
  return orders


def filter_executable_rows(rows: List[dict]) -> List[dict]:
  return [
    r for r in rows
    if r.get("row_type", "primary") == "primary"
    and r.get("gtc_tier") == "executable"
    and r.get("macro_mode") != "NUKE"
  ]
