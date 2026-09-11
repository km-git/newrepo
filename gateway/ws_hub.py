"""WebSocket hub — live ticker, book, trades with proxy + reconnect."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from gateway.proxy_pool import get_proxy_pool

try:
  import websockets
except ImportError:  # pragma: no cover
  websockets = None  # type: ignore


@dataclass
class StreamSnapshot:
  symbol: str
  exchange: str
  last: Optional[float] = None
  bid: Optional[float] = None
  ask: Optional[float] = None
  volume: Optional[float] = None
  book_imbalance: Optional[float] = None
  updated_at: float = field(default_factory=time.time)
  source: str = "ws"
  raw: Dict[str, Any] = field(default_factory=dict)


class WsHub:
  """
  Background WebSocket feeds for Kraken v2 + OKX v5 public channels.
  Falls back to REST poll when WS disabled or unavailable.
  """

  KRAKEN_WS = "wss://ws.kraken.com/v2"
  OKX_WS = "wss://ws.okx.com:8443/ws/v5/public"

  def __init__(self):
    self._snapshots: Dict[str, StreamSnapshot] = {}
    self._lock = threading.Lock()
    self._running = False
    self._thread: Optional[threading.Thread] = None
    self._symbols: List[str] = []
    self._exchange = os.environ.get("EW_WS_EXCHANGE", "okx").lower()

  def enabled(self) -> bool:
    return os.environ.get("EW_WS_ENABLED", "1").lower() not in ("0", "false", "no")

  def start(self, symbols: List[str], exchange: str = "") -> None:
    if not self.enabled() or websockets is None:
      return
    self._symbols = symbols[:20]
    if exchange:
      self._exchange = exchange.lower()
    if self._running:
      return
    self._running = True
    self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ws-hub")
    self._thread.start()

  def stop(self) -> None:
    self._running = False

  def get(self, symbol: str) -> Optional[StreamSnapshot]:
    key = symbol.upper()
    with self._lock:
      return self._snapshots.get(key)

  def all_snapshots(self) -> Dict[str, StreamSnapshot]:
    with self._lock:
      return dict(self._snapshots)

  def _run_loop(self) -> None:
    while self._running:
      try:
        asyncio.run(self._stream_all())
      except Exception as exc:
        print(f"[ws] hub error: {exc}")
        time.sleep(3)

  async def _stream_all(self) -> None:
    tasks = []
    for sym in self._symbols:
      if self._exchange == "kraken":
        tasks.append(self._kraken_ticker(sym))
      else:
        tasks.append(self._okx_ticker(sym))
    if tasks:
      await asyncio.gather(*tasks, return_exceptions=True)

  def _proxy_kw(self) -> dict:
    pool = get_proxy_pool()
    proxy = pool.next()
    if not proxy:
      return {}
    return {"proxy": proxy}

  async def _kraken_ticker(self, symbol: str) -> None:
    base = symbol.split("/")[0].replace("BTC", "XBT")
    pair = f"{base}/USD"
    sub = {
      "method": "subscribe",
      "params": {"channel": "ticker", "symbol": [pair], "event_trigger": "bbo"},
    }
    backoff = 1
    while self._running:
      try:
        async with websockets.connect(self.KRAKEN_WS, ping_interval=20, **self._proxy_kw()) as ws:
          await ws.send(json.dumps(sub))
          backoff = 1
          async for msg in ws:
            if not self._running:
              break
            data = json.loads(msg)
            if data.get("channel") != "ticker":
              continue
            tick = (data.get("data") or [{}])[0]
            last = float(tick.get("last") or tick.get("bid") or 0)
            bid = float(tick.get("bid") or 0)
            ask = float(tick.get("ask") or 0)
            self._update(symbol, "kraken", last, bid, ask, tick)
      except Exception as e:
        print(f"[ws] kraken {symbol}: {e}")
        await asyncio.sleep(min(backoff, 30))
        backoff *= 2

  async def _okx_ticker(self, symbol: str) -> None:
    inst = symbol.replace("/", "-")
    sub = {"op": "subscribe", "args": [{"channel": "tickers", "instId": inst}]}
    backoff = 1
    while self._running:
      try:
        async with websockets.connect(self.OKX_WS, ping_interval=20, **self._proxy_kw()) as ws:
          await ws.send(json.dumps(sub))
          backoff = 1
          async for msg in ws:
            if not self._running:
              break
            data = json.loads(msg)
            if data.get("event") or data.get("arg", {}).get("channel") != "tickers":
              continue
            rows = data.get("data") or []
            if not rows:
              continue
            tick = rows[0]
            last = float(tick.get("last") or 0)
            bid = float(tick.get("bidPx") or 0)
            ask = float(tick.get("askPx") or 0)
            vol = float(tick.get("vol24h") or 0)
            snap = self._update(symbol, "okx", last, bid, ask, tick)
            snap.volume = vol
      except Exception as e:
        print(f"[ws] okx {symbol}: {e}")
        await asyncio.sleep(min(backoff, 30))
        backoff *= 2

  def _update(
    self, symbol: str, exchange: str, last: float, bid: float, ask: float, raw: dict
  ) -> StreamSnapshot:
    imb = None
    if bid > 0 and ask > 0:
      mid = (bid + ask) / 2
      spread = ask - bid
      imb = round((mid - bid) / spread - 0.5, 3) if spread else 0
    snap = StreamSnapshot(
      symbol=symbol.upper(),
      exchange=exchange,
      last=last or None,
      bid=bid or None,
      ask=ask or None,
      book_imbalance=imb,
      updated_at=time.time(),
      raw=raw,
    )
    with self._lock:
      self._snapshots[symbol.upper()] = snap
    return snap


_hub: Optional[WsHub] = None


def get_ws_hub() -> WsHub:
  global _hub
  if _hub is None:
    _hub = WsHub()
  return _hub
