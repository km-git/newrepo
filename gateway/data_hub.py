"""Unified data hub — REST gateway + WebSocket + web intel + proxies."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd

from gateway.market_gateway import get_gateway
from gateway.proxy_pool import get_proxy_pool
from gateway.web_intel import build_web_intel
from gateway.ws_hub import get_ws_hub


def _merge_social_intel(intel: dict, symbol: str) -> dict:
  if os.environ.get("EW_SOCIAL_INTEL", "1").lower() in ("0", "false", "no"):
    return intel
  try:
    from gateway.social_intel import build_social_intel

    social = build_social_intel(symbol)
    intel = dict(intel)
    intel["social"] = social
    if social.get("signals"):
      intel["signals"] = list(intel.get("signals") or []) + social["signals"][:3]
  except Exception as exc:
    intel = dict(intel)
    intel["social"] = {"available": False, "error": str(exc)}
  return intel


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
      intel = _merge_social_intel(intel, symbol)
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
    # Upgrade orderbook proxy for microstructure when live WS available
    if not (tools.get("orderbook") or {}).get("available"):
      tools["orderbook"] = {
        "available": True,
        "imbalance": ws["imbalance"],
        "source": "ws_proxy",
      }
  web_intel = state.get("web_intel") or {}
  tools["web_intel"] = web_intel

  fg = web_intel.get("fear_greed") or {}
  if fg.get("available") and fg.get("value", 50) <= 25:
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + ["extreme fear"]
    tools["confluence_boost"] = min(int(tools.get("confluence_boost", 0)) + 3, 28)
  elif fg.get("available") and fg.get("value", 50) >= 75:
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + ["extreme greed"]
    tools["confluence_boost"] = min(int(tools.get("confluence_boost", 0)) + 2, 28)

  fc = web_intel.get("funding_cross") or {}
  if fc.get("available"):
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [
      f"funding {fc.get('consensus_bias')} ({fc.get('avg_funding_rate_pct')}%)"
    ]

  oi = web_intel.get("open_interest") or {}
  if oi.get("available") and oi.get("oi_change_24h_pct") is not None:
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [
      f"OI 24h {oi['oi_change_24h_pct']:+.1f}%"
    ]

  cs = web_intel.get("coin_stats") or {}
  if cs.get("available") and cs.get("momentum") != "neutral":
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [
      f"{cs['symbol']} momentum {cs['momentum']}"
    ]

  ls = web_intel.get("long_short_ratio") or {}
  if ls.get("available") and ls.get("bias") != "neutral":
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [
      f"L/S {ls.get('bias')} ({ls.get('long_short_ratio')})"
    ]

  liq = web_intel.get("liquidations") or {}
  if liq.get("available") and liq.get("bias") not in ("balanced", None):
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [
      f"liquidations {liq['bias']}"
    ]

  basis = web_intel.get("spot_perp_basis") or {}
  if basis.get("available") and basis.get("bias") != "neutral":
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [
      f"basis {basis['basis_pct']:+.2f}%"
    ]

  tv = tools.get("tv_confluence") or {}
  if tv.get("aligned"):
    tools["confluence_boost"] = min(int(tools.get("confluence_boost", 0)) + 5, 28)
    for sig in (tv.get("signals") or [])[:2]:
      tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [sig]

  social = web_intel.get("social") or {}
  for c in (social.get("candidates") or [])[:2]:
    if c.get("validation_prior") == "likely_valid":
      sig = f"social validated: {c.get('name')}"
      tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [sig]
      tools["confluence_boost"] = min(int(tools.get("confluence_boost", 0)) + 2, 25)
  oi = (state.get("web_intel") or {}).get("open_interest") or {}
  if oi.get("available"):
    tools["confluence_signals"] = list(tools.get("confluence_signals") or []) + [
      f"OI {oi.get('open_interest', 0):,.0f}"
    ]
    tools["confluence_boost"] = min(int(tools.get("confluence_boost", 0)) + 2, 28)
  return tools
