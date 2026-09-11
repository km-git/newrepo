"""CCXT broker — Kraken primary, OKX fallback for live/paper execution."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import ccxt

from engine.broker.symbol_map import for_ccxt


EXECUTION_CHAIN = tuple(
  x.strip()
  for x in os.environ.get("EW_EXECUTION_EXCHANGES", "kraken,okx").split(",")
  if x.strip()
)


def _make_exchange(exchange_id: str, *, sandbox: bool = False):
  cls = getattr(ccxt, exchange_id)
  opts: Dict[str, Any] = {"enableRateLimit": True}
  if exchange_id == "kraken":
    key = os.environ.get("KRAKEN_API_KEY", "").strip()
    secret = os.environ.get("KRAKEN_API_SECRET", "").strip()
    if key and secret:
      opts["apiKey"] = key
      opts["secret"] = secret
  elif exchange_id == "okx":
    key = os.environ.get("OKX_API_KEY", "").strip()
    secret = os.environ.get("OKX_API_SECRET", "").strip()
    passwd = os.environ.get("OKX_PASSWORD", "").strip()
    if key and secret:
      opts["apiKey"] = key
      opts["secret"] = secret
      if passwd:
        opts["password"] = passwd
  ex = cls(opts)
  if sandbox and hasattr(ex, "set_sandbox_mode"):
    ex.set_sandbox_mode(True)
  return ex


def _first_working_exchange(sandbox: bool = False):
  last_err = None
  for ex_id in EXECUTION_CHAIN:
    try:
      ex = _make_exchange(ex_id, sandbox=sandbox)
      if not ex.apiKey and os.environ.get("EW_EXECUTION_MODE", "paper") == "live":
        continue
      markets = ex.load_markets()
      return ex, ex_id, markets
    except Exception as e:
      last_err = e
      continue
  raise RuntimeError(f"No execution exchange available: {last_err}")


def fetch_ticker(symbol: str) -> Dict[str, Any]:
  ex, ex_id, _ = _first_working_exchange()
  sym = for_ccxt(symbol, ex_id)
  t = ex.fetch_ticker(sym)
  return {
    "symbol": symbol,
    "exchange": ex_id,
    "last": t.get("last"),
    "bid": t.get("bid"),
    "ask": t.get("ask"),
  }


def fetch_balance() -> Dict[str, Any]:
  ex, ex_id, _ = _first_working_exchange()
  if not ex.apiKey:
    return {"exchange": ex_id, "available": False, "error": "no_api_key"}
  bal = ex.fetch_balance()
  return {"exchange": ex_id, "total": bal.get("total"), "free": bal.get("free")}


def place_limit_order(
  *,
  symbol: str,
  side: str,
  amount: float,
  price: float,
  client_id: str = "",
  post_only: bool = True,
) -> Dict[str, Any]:
  ex, ex_id, markets = _first_working_exchange()
  sym = for_ccxt(symbol, ex_id)
  if sym not in markets:
    raise ValueError(f"Market {sym} not on {ex_id}")
  amount = float(ex.amount_to_precision(sym, amount))
  price = float(ex.price_to_precision(sym, price))
  params: Dict[str, Any] = {}
  if client_id:
    params["clientOrderId"] = client_id
  if post_only and ex_id in ("kraken", "okx"):
    params["postOnly"] = True
  order = ex.create_order(sym, "limit", side, amount, price, params)
  time.sleep(ex.rateLimit / 1000 if ex.rateLimit else 0.3)
  return {"ok": True, "exchange": ex_id, "order": order}


def place_stop_loss_limit(
  *,
  symbol: str,
  side: str,
  amount: float,
  trigger_price: float,
  limit_price: float,
) -> Dict[str, Any]:
  """Place stop-loss-limit (Kraken/OKX via ccxt params where supported)."""
  ex, ex_id, markets = _first_working_exchange()
  sym = for_ccxt(symbol, ex_id)
  amount = float(ex.amount_to_precision(sym, amount))
  trigger_price = float(ex.price_to_precision(sym, trigger_price))
  limit_price = float(ex.price_to_precision(sym, limit_price))
  params: Dict[str, Any] = {}
  if ex_id == "kraken":
    order = ex.create_order(
      sym, "stop-loss-limit", side, amount, limit_price,
      {**params, "stopPrice": trigger_price},
    )
  else:
    order = ex.create_order(
      sym, "stop_loss_limit", side, amount, limit_price,
      {**params, "stopPrice": trigger_price},
    )
  return {"ok": True, "exchange": ex_id, "order": order}


def cancel_order(symbol: str, order_id: str) -> Dict[str, Any]:
  ex, ex_id, _ = _first_working_exchange()
  sym = for_ccxt(symbol, ex_id)
  result = ex.cancel_order(order_id, sym)
  return {"ok": True, "exchange": ex_id, "result": result}


def fetch_open_orders(symbol: str = "") -> List[dict]:
  ex, ex_id, _ = _first_working_exchange()
  sym = for_ccxt(symbol, ex_id) if symbol else None
  return ex.fetch_open_orders(sym)


def cancel_all_orders(symbol: str = "") -> Dict[str, Any]:
  ex, ex_id, _ = _first_working_exchange()
  sym = for_ccxt(symbol, ex_id) if symbol else None
  if hasattr(ex, "cancel_all_orders"):
    return {"ok": True, "exchange": ex_id, "result": ex.cancel_all_orders(sym)}
  open_orders = ex.fetch_open_orders(sym)
  cancelled = []
  for o in open_orders:
    cancelled.append(ex.cancel_order(o["id"], o["symbol"]))
  return {"ok": True, "exchange": ex_id, "cancelled": len(cancelled)}
