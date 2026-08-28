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
  slug = slug_map.get(base)
  if not slug:
    search = _fetch_json(
      f"https://api.coingecko.com/api/v3/search?query={base}",
      host="coingecko.com",
    )
    if search and not search.get("error"):
      coins = search.get("coins") or []
      for c in coins:
        if str(c.get("symbol", "")).upper() == base:
          slug = c.get("id")
          break
  if not slug:
    slug = base.lower()
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


def _sym_usdt(symbol: str) -> str:
  base = symbol.split("/")[0].upper()
  return f"{base}USDT"


def binance_long_short_ratio(symbol: str = "BTC/USDT", period: str = "1h") -> Dict[str, Any]:
  """Binance futures global long/short account ratio (public)."""
  sym = _sym_usdt(symbol)
  url = (
    f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
    f"?symbol={sym}&period={period}&limit=1"
  )
  data = _fetch_json(url, host="fapi.binance.com")
  if not data or data.get("error") or not isinstance(data, list) or not data:
    return {"available": False}
  row = data[-1]
  ratio = float(row.get("longShortRatio") or 1)
  long_pct = round(ratio / (1 + ratio) * 100, 1)
  bias = "long_crowded" if ratio > 1.15 else "short_crowded" if ratio < 0.85 else "neutral"
  return {
    "available": True,
    "symbol": sym,
    "long_short_ratio": round(ratio, 4),
    "long_account_pct": long_pct,
    "bias": bias,
    "source": "binance",
  }


def binance_taker_ratio(symbol: str = "BTC/USDT", period: str = "1h") -> Dict[str, Any]:
  """Taker buy/sell volume ratio — aggressive flow direction."""
  sym = _sym_usdt(symbol)
  url = (
    f"https://fapi.binance.com/futures/data/takerlongshortRatio"
    f"?symbol={sym}&period={period}&limit=1"
  )
  data = _fetch_json(url, host="fapi.binance.com")
  if not data or data.get("error") or not isinstance(data, list) or not data:
    return {"available": False}
  row = data[-1]
  ratio = float(row.get("buySellRatio") or 1)
  bias = "buy_pressure" if ratio > 1.05 else "sell_pressure" if ratio < 0.95 else "neutral"
  return {
    "available": True,
    "symbol": sym,
    "buy_sell_ratio": round(ratio, 4),
    "bias": bias,
    "source": "binance",
  }


def spot_perp_basis(symbol: str = "BTC/USDT") -> Dict[str, Any]:
  """Spot–perp basis from Binance premium index (mark vs index)."""
  sym = _sym_usdt(symbol)
  url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}"
  data = _fetch_json(url, host="fapi.binance.com")
  if not data or data.get("error"):
    return {"available": False}
  mark = float(data.get("markPrice") or 0)
  index = float(data.get("indexPrice") or mark)
  if index <= 0:
    return {"available": False}
  basis_pct = round((mark - index) / index * 100, 4)
  bias = "contango" if basis_pct > 0.05 else "backwardation" if basis_pct < -0.05 else "neutral"
  return {
    "available": True,
    "symbol": sym,
    "basis_pct": basis_pct,
    "mark_price": mark,
    "index_price": index,
    "bias": bias,
    "source": "binance",
  }


def okx_open_interest(symbol: str = "BTC/USDT") -> Dict[str, Any]:
  base = symbol.split("/")[0].upper()
  inst = f"{base}-USDT-SWAP"
  url = f"https://www.okx.com/api/v5/public/open-interest?instId={inst}"
  data = _fetch_json(url, host="okx.com")
  if not data or data.get("error") or data.get("code") != "0":
    return {"available": False}
  rows = data.get("data") or []
  if not rows:
    return {"available": False}
  oi = float(rows[0].get("oi") or 0)
  return {"available": True, "symbol": inst, "open_interest": oi, "source": "okx"}


def bybit_open_interest(symbol: str = "BTC/USDT") -> Dict[str, Any]:
  sym = _sym_usdt(symbol)
  url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={sym}"
  data = _fetch_json(url, host="api.bybit.com")
  if not data or data.get("error") or data.get("retCode") != 0:
    return {"available": False}
  rows = (data.get("result") or {}).get("list") or []
  if not rows:
    return {"available": False}
  oi = float(rows[0].get("openInterest") or 0)
  return {"available": True, "symbol": sym, "open_interest": oi, "source": "bybit"}


def oi_cross_check(symbol: str) -> Dict[str, Any]:
  """Cross-venue open interest snapshot."""
  sources = {
    "binance": binance_open_interest(symbol),
    "okx": okx_open_interest(symbol),
    "bybit": bybit_open_interest(symbol),
  }
  vals = {k: v["open_interest"] for k, v in sources.items() if v.get("available")}
  if not vals:
    return {"available": False}
  total = sum(vals.values())
  return {
    "available": True,
    "total_oi": round(total, 2),
    "sources": vals,
    "count": len(vals),
  }


def binance_recent_liquidations(symbol: str = "BTC/USDT", limit: int = 20) -> Dict[str, Any]:
  """Recent force-liquidation orders from Binance public API."""
  sym = _sym_usdt(symbol)
  url = f"https://fapi.binance.com/fapi/v1/allForceOrders?symbol={sym}&limit={limit}"
  data = _fetch_json(url, host="fapi.binance.com")
  if not data or data.get("error") or not isinstance(data, list):
    return {"available": False}
  long_liq = sum(1 for o in data if o.get("side") == "SELL")
  short_liq = sum(1 for o in data if o.get("side") == "BUY")
  bias = "long_liquidated" if long_liq > short_liq else "short_liquidated" if short_liq > long_liq else "balanced"
  return {
    "available": True,
    "symbol": sym,
    "count": len(data),
    "long_liq_count": long_liq,
    "short_liq_count": short_liq,
    "bias": bias,
    "source": "binance",
  }


def defillama_total_tvl() -> Dict[str, Any]:
  data = _fetch_json("https://api.llama.fi/v2/historicalChainTvl", host="api.llama.fi")
  if not data or not isinstance(data, list) or not data:
    if isinstance(data, dict) and data.get("error"):
      return {"available": False, "error": data.get("error")}
    return {"available": False}
  latest = data[-1]
  tvl = float(latest.get("tvl") or 0)
  prev = float(data[-2].get("tvl") or tvl) if len(data) > 1 else tvl
  chg = round((tvl - prev) / prev * 100, 2) if prev else 0
  return {
    "available": True,
    "total_tvl_usd": round(tvl, 0),
    "tvl_change_pct": chg,
    "source": "defillama",
  }


def macro_tradfi_snapshot() -> Dict[str, Any]:
  """DXY / VIX / SPY via yfinance — macro risk context for BTC."""
  try:
    import yfinance as yf
  except ImportError:
    return {"available": False, "reason": "yfinance not installed"}
  out: Dict[str, Any] = {"available": True, "tickers": {}, "source": "yfinance"}
  for ticker, label in (("DX-Y.NYB", "dxy"), ("^VIX", "vix"), ("SPY", "spy")):
    try:
      hist = yf.Ticker(ticker).history(period="5d")
      if hist is None or len(hist) < 2:
        continue
      chg = float((hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100)
      out["tickers"][label] = {"change_1d_pct": round(chg, 2)}
    except Exception:
      continue
  if not out["tickers"]:
    return {"available": False}
  vix = (out["tickers"].get("vix") or {}).get("change_1d_pct", 0)
  out["risk_bias"] = "risk_off" if vix > 3 else "risk_on" if vix < -3 else "neutral"
  return out


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


def okx_funding_public(symbol: str = "BTC/USDT") -> Dict[str, Any]:
  """OKX public funding rate — fallback when Binance returns 451."""
  sym = symbol.replace("/", "-").upper()
  if not sym.endswith("-USDT"):
    sym += "-USDT"
  inst = f"{sym}-SWAP"
  data = _fetch_json(
    f"https://www.okx.com/api/v5/public/funding-rate?instId={inst}",
    host="www.okx.com",
  )
  if not data or data.get("error"):
    return {"available": False, "source": "okx"}
  rows = data.get("data") or []
  if not rows:
    return {"available": False, "source": "okx"}
  row = rows[0]
  try:
    rate = float(row.get("fundingRate") or 0)
  except (TypeError, ValueError):
    rate = 0.0
  return {
    "available": True,
    "symbol": inst,
    "funding_rate": rate,
    "funding_rate_pct": round(rate * 100, 4),
    "source": "okx",
  }


def build_web_intel(symbol: str = "") -> Dict[str, Any]:
  """Aggregate all free web/API intel for execution pre-flight."""
  intel: Dict[str, Any] = {
    "fear_greed": fear_greed_index(),
    "global": coingecko_global(),
    "stablecoins": defillama_stablecoins(),
    "defi_tvl": defillama_total_tvl(),
    "macro_tradfi": macro_tradfi_snapshot(),
  }
  if symbol:
    intel["coin_stats"] = coingecko_coin_stats(symbol)
    fb = binance_funding_public(symbol)
    intel["funding_binance"] = fb
    intel["funding_okx"] = okx_funding_public(symbol)
    intel["funding_bybit"] = bybit_funding_public(symbol)
    intel["funding_cross"] = funding_cross_check(symbol)
    intel["open_interest"] = binance_open_interest(symbol)
    if not intel["open_interest"].get("available"):
      oi_okx = okx_open_interest(symbol)
      if oi_okx.get("available"):
        intel["open_interest"] = oi_okx
    intel["oi_cross"] = oi_cross_check(symbol)
    intel["long_short_ratio"] = binance_long_short_ratio(symbol)
    intel["taker_ratio"] = binance_taker_ratio(symbol)
    intel["spot_perp_basis"] = spot_perp_basis(symbol)
    intel["liquidations"] = binance_recent_liquidations(symbol)
    if not fb.get("available") and intel["funding_okx"].get("available"):
      intel["funding"] = intel["funding_okx"]
    elif fb.get("available"):
      intel["funding"] = fb
    else:
      intel["funding"] = intel.get("funding_okx") or {"available": False}
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
  if oi.get("available"):
    if oi.get("oi_change_24h_pct") is not None:
      signals.append(f"OI 24h {oi['oi_change_24h_pct']:+.1f}%")
    elif oi.get("open_interest"):
      signals.append(f"OI {oi['open_interest']:,.0f}")
  ls = intel.get("long_short_ratio") or {}
  if ls.get("available"):
    signals.append(f"L/S ratio {ls.get('long_short_ratio')} ({ls.get('bias')})")
  tk = intel.get("taker_ratio") or {}
  if tk.get("available") and tk.get("bias") != "neutral":
    signals.append(f"taker {tk['bias']}")
  basis = intel.get("spot_perp_basis") or {}
  if basis.get("available") and basis.get("bias") != "neutral":
    signals.append(f"basis {basis['basis_pct']:+.3f}% ({basis['bias']})")
  liq = intel.get("liquidations") or {}
  if liq.get("available") and liq.get("count", 0) > 0:
    signals.append(f"liq {liq['bias']} ({liq['count']} recent)")
  tvl = intel.get("defi_tvl") or {}
  if tvl.get("available"):
    signals.append(f"DeFi TVL ${tvl['total_tvl_usd']/1e9:.0f}B")
  macro = intel.get("macro_tradfi") or {}
  if macro.get("available") and macro.get("risk_bias") != "neutral":
    signals.append(f"macro {macro['risk_bias']}")

  intel["signals"] = signals
  return intel
