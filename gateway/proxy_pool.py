"""Rotating proxy pool for REST + WebSocket — file or env driven."""

from __future__ import annotations

import os
import random
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProxyPool:
  """
  Round-robin / random proxy rotation.
  Sources (priority):
    1. EW_PROXY_LIST env (comma-separated URLs)
    2. EW_PROXY_FILE path (one proxy per line)
    3. HTTP_PROXY / HTTPS_PROXY / WS_PROXY env singles
  """

  def __init__(self, proxies: Optional[List[str]] = None):
    self._lock = threading.Lock()
    self._index = 0
    self._failures: Dict[str, int] = {}
    self._cooldown_until: Dict[str, float] = {}
    self._proxies = proxies if proxies is not None else _load_proxies()

  @property
  def enabled(self) -> bool:
    return bool(self._proxies)

  def all(self) -> List[str]:
    return list(self._proxies)

  def next(self, strategy: str = "") -> Optional[str]:
    if not self._proxies:
      return None
    strategy = strategy or os.environ.get("EW_PROXY_STRATEGY", "round_robin")
    now = time.time()
    alive = [
      p for p in self._proxies
      if self._cooldown_until.get(p, 0) <= now
    ]
    if not alive:
      alive = self._proxies
    with self._lock:
      if strategy == "random":
        return random.choice(alive)
      proxy = alive[self._index % len(alive)]
      self._index += 1
      return proxy

  def mark_failure(self, proxy: str, cooldown_sec: float = 60) -> None:
    if not proxy:
      return
    self._failures[proxy] = self._failures.get(proxy, 0) + 1
    self._cooldown_until[proxy] = time.time() + cooldown_sec

  def mark_success(self, proxy: str) -> None:
    if proxy:
      self._failures.pop(proxy, None)
      self._cooldown_until.pop(proxy, None)

  def apply_to_ccxt(self, exchange, proxy: Optional[str] = None) -> str:
    """Set ccxt proxy attrs; return proxy used."""
    proxy = proxy or self.next()
    if not proxy:
      return ""
    if proxy.startswith("socks"):
      exchange.socks_proxy = proxy
      if hasattr(exchange, "ws_socks_proxy"):
        exchange.ws_socks_proxy = proxy
    else:
      exchange.http_proxy = proxy
      exchange.https_proxy = proxy
      if hasattr(exchange, "ws_proxy"):
        exchange.ws_proxy = proxy
    return proxy

  def stats(self) -> Dict[str, Any]:
    return {
      "count": len(self._proxies),
      "failures": dict(self._failures),
      "cooldown": {k: max(0, v - time.time()) for k, v in self._cooldown_until.items()},
    }


_pool: Optional[ProxyPool] = None


def get_proxy_pool() -> ProxyPool:
  global _pool
  if _pool is None:
    _pool = ProxyPool()
  return _pool


def _load_proxies() -> List[str]:
  raw = os.environ.get("EW_PROXY_LIST", "").strip()
  if raw:
    return [p.strip() for p in raw.split(",") if p.strip()]
  path = os.environ.get("EW_PROXY_FILE", "").strip()
  if path and Path(path).exists():
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
  singles = []
  for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "WS_PROXY", "WSS_PROXY"):
    val = os.environ.get(key, "").strip()
    if val:
      singles.append(val)
  return list(dict.fromkeys(singles))
