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


def coingecko_coin_stats(symbol: str) -> Dict[str, Any]:
  """Per-coin 24h change + volume from CoinGecko (free, no key)."""
  base = symbol.split("/")[0].upper()
  slug_map = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple",
    "DOGE": "dogecoin", "ADA": "cardano", "AVAX": "avalanche-2", "DOT": "polkadot",
    "LINK": "chainlink", "MATIC": "matic-network", "UNI": "uniswap", "ATOM": "cosmos",
    "LTC": "litecoin", "BCH": "bitcoin-cash", "NEAR": "near", "APT": "aptos",
    "ARB": "arbitrum", "OP": "optimism", "SUI": "sui", "SEI": "sei-network",
  }
  slug = slug_map.get(base, base.lower())
  url = (
    f"https://api.coingecko.com/api/v3/simple/price"
    f"?ids={slug}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
  )
  data = _fetch_json(url, host="coingecko.com")
  if not data or data.get("error") or slug not in data:
    return {"available": False, "symbol": base}
  row = data[slug]
  chg = float(row.get("usd_24h_change") or 0)
  return {
    "available": True,
    "symbol": base,
    "price_usd": row.get("usd"),
    "change_24h_pct": round(chg, 2),
    "volume_24h_usd": row.get("usd_24h_vol"),
    "momentum": "bullish" if chg > 2 else "bearish" if chg < -2 else "neutral",
    "source": "coingecko",
  }


def defillama_stablecoins() -> Dict[str, Any]:
  """DeFiLlama stablecoin market cap — liquidity/risk regime signal."""
  data = _fetch_json("https://stablecoins.llama.fi/stablecoins?includePrices=true", host="stablecoins.llama.fi")
  if not data or data.get("error"):
    return {"available": False}
  pegged = data.get("peggedAssets") or []
  total = sum(float(p.get("circulating", {}).get("peggedUSD", 0) or 0) for p in pegged[:50])
  return {
    "available": True,
    "total_stablecoin_mcap_usd": round(total, 0),
    "count": len(pegged),
    "source": "defillama",
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
    "source": "binance",
  }


def okx_funding_public(symbol: str = "BTC/USDT") -> Dict[str, Any]:
  """OKX public funding rate (no auth)."""
  base = symbol.split("/")[0].upper()
  inst = f"{base}-USDT-SWAP"
  url = f"https://www.okx.com/api/v5/public/funding-rate?instId={inst}"
  data = _fetch_json(url, host="okx.com")
  if not data or data.get("error") or data.get("code") != "0":
    return {"available": False}
  rows = data.get("data") or []
  if not rows:
    return {"available": False}
  rate = float(rows[0].get("fundingRate") or 0)
  return {
    "available": True,
    "symbol": inst,
    "funding_rate": rate,
    "funding_rate_pct": round(rate * 100, 4),
    "source": "okx",
  }


def bybit_funding_public(symbol: str = "BTC/USDT") -> Dict[str, Any]:
  """Bybit public funding rate (no auth)."""
  base = symbol.split("/")[0].upper()
  sym = f"{base}USDT"
  url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={sym}"
  data = _fetch_json(url, host="api.bybit.com")
  if not data or data.get("error") or data.get("retCode") != 0:
    return {"available": False}
  rows = (data.get("result") or {}).get("list") or []
  if not rows:
    return {"available": False}
  rate = float(rows[0].get("fundingRate") or 0)
  return {
    "available": True,
    "symbol": sym,
    "funding_rate": rate,
    "funding_rate_pct": round(rate * 100, 4),
    "source": "bybit",
  }


def binance_open_interest(symbol: str = "BTC/USDT") -> Dict[str, Any]:
  """Binance futures open interest (public, no auth)."""
  base = symbol.split("/")[0].upper()
  sym = f"{base}USDT"
  url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={sym}"
  data = _fetch_json(url, host="fapi.binance.com")
  if not data or data.get("error"):
    return {"available": False}
  oi = float(data.get("openInterest") or 0)
  # 24h change via historical OI endpoint
  hist_url = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={sym}&period=1d&limit=2"
  hist = _fetch_json(hist_url, host="fapi.binance.com")
  oi_chg = None
  if hist and isinstance(hist, list) and len(hist) >= 2:
    prev = float(hist[-2].get("sumOpenInterest", 0) or 0)
    if prev > 0:
      oi_chg = round((oi - prev) / prev * 100, 2)
  return {
    "available": True,
    "symbol": sym,
    "open_interest": oi,
    "oi_change_24h_pct": oi_chg,
    "source": "binance",
  }


def funding_cross_check(symbol: str) -> Dict[str, Any]:
  """Aggregate funding across Binance, OKX, Bybit — crowd positioning signal."""
  sources = {
    "binance": binance_funding_public(symbol),
    "okx": okx_funding_public(symbol),
    "bybit": bybit_funding_public(symbol),
  }
  rates = [s["funding_rate"] for s in sources.values() if s.get("available")]
  if not rates:
    return {"available": False}
  avg = sum(rates) / len(rates)
  bias = "long_crowded" if avg > 0.0001 else "short_crowded" if avg < -0.0001 else "neutral"
  return {
    "available": True,
    "avg_funding_rate": round(avg, 6),
    "avg_funding_rate_pct": round(avg * 100, 4),
    "consensus_bias": bias,
    "sources": {k: v.get("funding_rate_pct") for k, v in sources.items() if v.get("available")},
    "count": len(rates),
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
  """Aggregate all free web/API intel for execution pre-flight."""
  intel: Dict[str, Any] = {
    "fear_greed": fear_greed_index(),
    "global": coingecko_global(),
    "stablecoins": defillama_stablecoins(),
  }
  if symbol:
    intel["coin_stats"] = coingecko_coin_stats(symbol)
    intel["funding_binance"] = binance_funding_public(symbol)
    intel["funding_okx"] = okx_funding_public(symbol)
    intel["funding_bybit"] = bybit_funding_public(symbol)
    intel["funding_cross"] = funding_cross_check(symbol)
    intel["open_interest"] = binance_open_interest(symbol)

  signals: List[str] = []
  fg = intel["fear_greed"]
  if fg.get("available"):
    signals.append(f"Fear&Greed {fg['value']} ({fg['label']})")
  gl = intel["global"]
  if gl.get("available"):
    signals.append(f"BTC.D {gl.get('btc_dominance')}%")
    chg = gl.get("market_cap_change_24h_pct")
    if chg is not None:
      signals.append(f"mkt cap 24h {chg:+.1f}%")
  sc = intel.get("stablecoins") or {}
  if sc.get("available"):
    signals.append(f"stablecoins ${sc['total_stablecoin_mcap_usd']/1e9:.0f}B")
  cs = intel.get("coin_stats") or {}
  if cs.get("available"):
    signals.append(f"{cs['symbol']} 24h {cs.get('change_24h_pct', 0):+.1f}%")
  fc = intel.get("funding_cross") or {}
  if fc.get("available"):
    signals.append(f"funding avg {fc['avg_funding_rate_pct']}% ({fc['consensus_bias']})")
  oi = intel.get("open_interest") or {}
  if oi.get("available") and oi.get("oi_change_24h_pct") is not None:
    signals.append(f"OI 24h {oi['oi_change_24h_pct']:+.1f}%")

  intel["signals"] = signals
  return intel
