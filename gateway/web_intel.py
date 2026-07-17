"""Web intelligence — scrape/API hybrid for macro + sentiment + on-chain signals."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from gateway.antibot import browser_headers, get_rate_limiter, jitter_delay
from gateway.proxy_pool import get_proxy_pool


def _fetch_json(url: str, *, host: str = "", timeout: int = 15) -> Optional[dict]:
  get_rate_limiter().wait(host or url.split("/")[2])
  jitter_delay()
  headers = browser_headers()
  headers["Accept-Encoding"] = "identity"
  proxy = get_proxy_pool().next()
  handlers = []
  if proxy:
    handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
  opener = urllib.request.build_opener(*handlers)
  req = urllib.request.Request(url, headers=headers)
  try:
    with opener.open(req, timeout=timeout) as resp:
      return json.loads(resp.read().decode())
  except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
    if proxy:
      get_proxy_pool().mark_failure(proxy)
    return {"error": str(e), "url": url}


def fear_greed_index() -> Dict[str, Any]:
  """Alternative.me Crypto Fear & Greed (public JSON API)."""
  data = _fetch_json("https://api.alternative.me/fng/?limit=1", host="alternative.me")
  if not data or data.get("error"):
    return {"available": False, "error": (data or {}).get("error", "fetch_failed")}
  row = (data.get("data") or [{}])[0]
  val = int(row.get("value", 50))
  label = row.get("value_classification", "Neutral")
  bias = "risk_on" if val >= 55 else "risk_off" if val <= 45 else "neutral"
  return {
    "available": True,
    "value": val,
    "label": label,
    "bias": bias,
    "timestamp": row.get("timestamp"),
  }


def coingecko_global() -> Dict[str, Any]:
  """Global market cap / dominance snapshot."""
  data = _fetch_json("https://api.coingecko.com/api/v3/global", host="coingecko.com")
  if not data or data.get("error"):
    return {"available": False}
  g = data.get("data") or {}
  mcp = g.get("market_cap_percentage") or {}
  return {
    "available": True,
    "btc_dominance": round(float(mcp.get("btc", 0)), 2),
    "eth_dominance": round(float(mcp.get("eth", 0)), 2),
    "total_market_cap_usd": g.get("total_market_cap", {}).get("usd"),
    "market_cap_change_24h_pct": g.get("market_cap_change_percentage_24h_usd"),
  }


def binance_funding_public(symbol: str = "BTCUSDT") -> Dict[str, Any]:
  """Public Binance futures funding (no auth) — cross-check."""
  sym = symbol.replace("/", "").upper()
  if not sym.endswith("USDT"):
    sym += "USDT"
  url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}"
  data = _fetch_json(url, host="fapi.binance.com")
  if not data or data.get("error"):
    return {"available": False}
  rate = float(data.get("lastFundingRate") or 0)
  return {
    "available": True,
    "symbol": sym,
    "funding_rate": rate,
    "funding_rate_pct": round(rate * 100, 4),
    "mark_price": float(data.get("markPrice") or 0),
    "source": "binance_public",
  }


def scrape_page_text(url: str, max_chars: int = 4000) -> Dict[str, Any]:
  """
  Polite HTML fetch with anti-bot headers.
  Strips tags lightly — for headline/sentiment extraction, not full parse.
  """
  if os.environ.get("EW_SCRAPE_ENABLED", "1").lower() in ("0", "false", "no"):
    return {"available": False, "reason": "EW_SCRAPE_ENABLED=0"}
  get_rate_limiter().wait(url.split("/")[2])
  jitter_delay(300, 600)
  headers = browser_headers(referer="https://www.google.com/")
  proxy = get_proxy_pool().next()
  handlers = []
  if proxy:
    handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
  opener = urllib.request.build_opener(*handlers)
  req = urllib.request.Request(url, headers=headers)
  try:
    with opener.open(req, timeout=20) as resp:
      html = resp.read().decode("utf-8", errors="ignore")[:max_chars * 2]
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()[:max_chars]
    if proxy:
      get_proxy_pool().mark_success(proxy)
    return {"available": True, "url": url, "text": text, "chars": len(text)}
  except Exception as e:
    if proxy:
      get_proxy_pool().mark_failure(proxy)
    return {"available": False, "url": url, "error": str(e)}


def build_web_intel(symbol: str = "") -> Dict[str, Any]:
  """Aggregate web/API intel for execution pre-flight."""
  intel: Dict[str, Any] = {
    "fear_greed": fear_greed_index(),
    "global": coingecko_global(),
  }
  if symbol:
    intel["funding_binance"] = binance_funding_public(symbol)
  signals: List[str] = []
  fg = intel["fear_greed"]
  if fg.get("available"):
    signals.append(f"Fear&Greed {fg['value']} ({fg['label']})")
  gl = intel["global"]
  if gl.get("available"):
    signals.append(f"BTC.D {gl.get('btc_dominance')}%")
  intel["signals"] = signals
  return intel
