"""Unified data hub — REST gateway + WebSocket + web intel + proxies."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd

from gateway.market_gateway import get_gateway
from gateway.proxy_pool import get_proxy_pool
from gateway.web_intel import build_web_intel
from gateway.ws_hub import get_ws_hub


def data_hub_enabled() -> bool:
  return os.environ.get("EW_DATA_HUB", "1").lower() not in ("0", "false", "no")


def fetch_ohlcv_multi(
  symbol: str,
  timeframes: List[str],
  *,
  exchange_preference: Optional[str] = None,
) -> Dict[str, Any]:
  """
  OHLCV via semantic gateway + optional multi-exchange fallback chain.
  Set EW_OHLCV_CHAIN=okx,kraken,binance for broader sourcing.
  """
  chain = os.environ.get("EW_OHLCV_CHAIN", "okx").strip()
  pref = exchange_preference or (chain.split(",")[0] if chain else "okx")
  gw = get_gateway()
  resp = gw.fetch_ohlcv(symbol, timeframes, exchange_preference=pref)
  return {
    "data": resp.data,
    "exchange": resp.exchange_used,
    "cache_hits": resp.cache_hits,
    "latency_ms": resp.latency_ms,
    "proxy": get_proxy_pool().stats() if get_proxy_pool().enabled else None,
  }


def live_market_state(symbol: str, *, start_ws: bool = True) -> Dict[str, Any]:
  """Combine WS ticker + web intel + optional REST ticker."""
  hub = get_ws_hub()
  if start_ws and hub.enabled():
    hub.start([symbol], exchange=os.environ.get("EW_WS_EXCHANGE", "okx"))
  snap = hub.get(symbol)
  intel = {}
  if data_hub_enabled() and os.environ.get("EW_WEB_INTEL", "1").lower() not in ("0", "false", "no"):
    try:
      intel = build_web_intel(symbol)
    except Exception as exc:
      intel = {"error": str(exc)}
  state: Dict[str, Any] = {
    "symbol": symbol,
    "ws": {
      "enabled": hub.enabled(),
      "last": snap.last if snap else None,
      "bid": snap.bid if snap else None,
      "ask": snap.ask if snap else None,
      "imbalance": snap.book_imbalance if snap else None,
      "exchange": snap.exchange if snap else None,
      "age_sec": round(__import__("time").time() - snap.updated_at, 1) if snap else None,
    },
    "web_intel": intel,
    "proxy_pool": get_proxy_pool().stats(),
  }
  if snap and snap.last:
    state["mid"] = (snap.bid + snap.ask) / 2 if snap.bid and snap.ask else snap.last
  return state


def enrich_market_tools(symbol: str, data: Dict[str, pd.DataFrame], tools: dict) -> dict:
  """Layer WS + web intel onto existing market_tools block."""
  if not data_hub_enabled():
    return tools
  state = live_market_state(symbol, start_ws=True)
  tools = dict(tools)
  tools["live_ws"] = state.get("ws")
  tools["web_intel"] = state.get("web_intel")
  ws = state.get("ws") or {}
  if ws.get("imbalance") is not None and abs(ws["imbalance"]) > 0.1:
    sig = f"WS book imb {ws['imbalance']:+.2f}"
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [sig]
    tools["confluence_boost"] = min(int(tools.get("confluence_boost", 0)) + 3, 25)
  fg = (state.get("web_intel") or {}).get("fear_greed") or {}
  if fg.get("available") and fg.get("value", 50) <= 25:
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + ["extreme fear"]
  return tools
