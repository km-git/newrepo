"""Fetch top crypto pairs by 24h quote volume via ccxt."""

from __future__ import annotations

import time
from typing import List

import ccxt

EXCHANGE_CHAIN = ["okx"]
STABLES = {
  "USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FDUSD", "USDG", "EUR", "USD",
  "RLUSD", "PYUSD", "USDE", "USDS", "USD1", "USDD", "EURC", "FRAX", "LUSD", "DOLA", "GHO",
}


def _make_exchange(name: str):
  return getattr(ccxt, name)({"enableRateLimit": True})


def fetch_top_pairs(
  n: int = 50,
  quote: str = "USDT",
  min_volume_usd: float = 0,
  exchange_preference: str | None = None,
) -> List[str]:
  """
  Return top N BASE/QUOTE spot pairs sorted by 24h quote volume (OKX only).
  """
  return _fetch_okx_spot_pairs(n=n, quote=quote, min_volume_usd=min_volume_usd)


def fetch_scanner_pairs(
  n: int = 1000,
  quote: str = "USDT",
  *,
  include_swap: bool = True,
  min_volume_usd: float = 0,
  max_spread_bps: float = 35.0,
) -> List[str]:
  """
  Build scanner universe up to n symbols: OKX spot USDT + optional USDT perps.
  OKX spot caps ~395 USDT pairs; swaps add ~400+ for broader coverage toward 1000.
  """
  spot = _fetch_okx_spot_pairs(
    n=n,
    quote=quote,
    min_volume_usd=min_volume_usd,
    max_spread_bps=max_spread_bps,
  )
  pairs: List[str] = list(spot)

  if include_swap and len(pairs) < n:
    try:
      ex = _make_exchange("okx")
      ex.load_markets()
      existing = set(pairs)
      swap_tickers = ex.fetch_tickers(params={"instType": "SWAP"})
      swap_cands: list[tuple[str, float]] = []
      for sym, t in swap_tickers.items():
        if not sym.endswith(f":{quote}") or "/" not in sym:
          continue
        if sym in existing:
          continue
        base = sym.split("/")[0]
        if base in STABLES or base.startswith("1000"):
          continue
        market = ex.markets.get(sym, {})
        if market.get("active") is False:
          continue
        last = float(t.get("last") or 0)
        if last <= 0:
          continue
        vol = float(t.get("quoteVolume") or t.get("baseVolume") or 0)
        if last and t.get("baseVolume") and not t.get("quoteVolume"):
          vol = float(t["baseVolume"]) * last
        if vol < min_volume_usd:
          continue
        bid = float(t.get("bid") or 0)
        ask = float(t.get("ask") or 0)
        if bid > 0 and ask > bid and max_spread_bps > 0:
          mid = (bid + ask) / 2.0
          if (ask - bid) / mid * 10_000 > max_spread_bps:
            continue
        swap_cands.append((sym, vol))
      swap_cands.sort(key=lambda x: x[1], reverse=True)
      for sym, _ in swap_cands:
        if len(pairs) >= n:
          break
        pairs.append(sym)
        existing.add(sym)
    except Exception as e:
      print(f"[pairs] swap fetch skipped: {e}")

  print(f"[pairs] Scanner universe: {len(pairs)} symbols (target={n}, swap={include_swap})")
  return pairs[:n]


def _fetch_okx_spot_pairs(
  n: int = 50,
  quote: str = "USDT",
  min_volume_usd: float = 0,
  max_spread_bps: float = 0,
) -> List[str]:
  chain = ["okx"]
  last_err = None
  for ex_name in chain:
    try:
      ex = _make_exchange(ex_name)
      ex.load_markets()
      tickers = ex.fetch_tickers()
      candidates: list[tuple[str, float]] = []

      for sym, t in tickers.items():
        if not sym.endswith(f"/{quote}"):
          continue
        if ":USDT" in sym or "/" not in sym:
          continue
        base = sym.split("/")[0]
        if base in STABLES or base.startswith("1000"):
          continue
        market = ex.markets.get(sym, {})
        if market.get("active") is False:
          continue
        if market.get("spot") is False and market.get("type") not in (None, "spot", "swap"):
          continue
        last = float(t.get("last") or 0)
        if last <= 0:
          continue
        vol = float(t.get("quoteVolume") or t.get("baseVolume") or 0)
        if last and t.get("baseVolume") and not t.get("quoteVolume"):
          vol = float(t["baseVolume"]) * last
        if vol < min_volume_usd:
          continue
        bid = float(t.get("bid") or 0)
        ask = float(t.get("ask") or 0)
        if bid > 0 and ask > bid and max_spread_bps > 0:
          mid = (bid + ask) / 2.0
          if (ask - bid) / mid * 10_000 > max_spread_bps:
            continue
        candidates.append((sym, vol))

      if not candidates:
        raise ValueError(f"No {quote} pairs with volume on {ex_name}")

      candidates.sort(key=lambda x: x[1], reverse=True)
      pairs = [s for s, _ in candidates[:n]]
      print(f"[pairs] Top {len(pairs)} from {ex_name} (quote={quote})")
      for i, (s, v) in enumerate(candidates[: min(10, len(candidates))]):
        print(f"  {i+1}. {s} vol={v:,.0f}")
      return pairs
    except Exception as e:
      last_err = e
      print(f"[pairs] {ex_name} failed: {e}")
      time.sleep(1)
      continue
  raise RuntimeError(f"Could not fetch top pairs: {last_err}")


def write_pairs_csv(pairs: List[str], path: str, crypto: bool = True) -> None:
  import csv

  with open(path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["symbol", "crypto"])
    for p in pairs:
      w.writerow([p, "true" if crypto else "false"])
