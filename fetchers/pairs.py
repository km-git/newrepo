"""Fetch top crypto pairs by 24h quote volume via ccxt."""

from __future__ import annotations

import time
from typing import List

import ccxt

EXCHANGE_CHAIN = ["okx", "bybit", "kraken", "binance"]
STABLES = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FDUSD", "USDG", "EUR", "USD"}


def _make_exchange(name: str):
  return getattr(ccxt, name)({"enableRateLimit": True})


def fetch_top_pairs(
  n: int = 50,
  quote: str = "USDT",
  min_volume_usd: float = 0,
) -> List[str]:
  """
  Return top N BASE/QUOTE spot pairs sorted by 24h quote volume.
  Tries okx → bybit → binance.
  """
  last_err = None
  for ex_name in EXCHANGE_CHAIN:
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
        vol = float(t.get("quoteVolume") or t.get("baseVolume") or 0)
        if t.get("last") and t.get("baseVolume") and not t.get("quoteVolume"):
          vol = float(t["baseVolume"]) * float(t["last"])
        if vol < min_volume_usd:
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
