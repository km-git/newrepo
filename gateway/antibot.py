"""Anti-bot helpers — UA rotation, polite rate limits, header jitter."""

from __future__ import annotations

import os
import random
import time
from typing import Any, Dict, Optional

# Common browser UAs — rotate to reduce fingerprint blocking
USER_AGENTS = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

ACCEPT_LANGUAGES = [
  "en-US,en;q=0.9",
  "en-GB,en;q=0.9",
  "en-US,en;q=0.8,es;q=0.6",
]


class PoliteRateLimiter:
  """Token-bucket style min interval between requests per host."""

  def __init__(self, min_interval_ms: Optional[float] = None):
    self._min = (min_interval_ms or float(os.environ.get("EW_SCRAPE_MIN_MS", "800"))) / 1000.0
    self._last: Dict[str, float] = {}

  def wait(self, host: str = "default") -> None:
    now = time.time()
    prev = self._last.get(host, 0)
    gap = self._min - (now - prev)
    if gap > 0:
      time.sleep(gap)
    self._last[host] = time.time()


_limiter = PoliteRateLimiter()


def get_rate_limiter() -> PoliteRateLimiter:
  return _limiter


def random_user_agent() -> str:
  custom = os.environ.get("EW_USER_AGENT", "").strip()
  if custom:
    return custom
  return random.choice(USER_AGENTS)


def browser_headers(*, referer: str = "", extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
  """HTTP headers that mimic a real browser session."""
  h = {
    "User-Agent": random_user_agent(),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": random.choice(ACCEPT_LANGUAGES),
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
  }
  if referer:
    h["Referer"] = referer
  if extra:
    h.update(extra)
  return h


def jitter_delay(base_ms: float = 200, spread_ms: float = 400) -> None:
  """Random sleep to avoid robotic timing patterns."""
  if os.environ.get("EW_ANTIBOT_JITTER", "1").lower() in ("0", "false", "no"):
    return
  time.sleep((base_ms + random.random() * spread_ms) / 1000.0)
