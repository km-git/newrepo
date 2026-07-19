"""
Social & forum strategy intel — discover popular narratives, question hype,
and surface candidates for multi-AI executive validation.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from gateway.web_intel import scrape_page_text


def social_intel_enabled() -> bool:
  return os.environ.get("EW_SOCIAL_INTEL", "1").lower() not in ("0", "false", "no")


# Curated high-mention strategies from CT, Reddit, TradingView forums
FORUM_STRATEGY_CATALOG: Tuple[Dict[str, Any], ...] = (
  {
    "id": "rsi_divergence",
    "name": "RSI Divergence Reversal",
    "category": "indicator",
    "keywords": ("rsi divergence", "bullish divergence", "bearish divergence", "hidden divergence"),
    "our_signal": "rsi_stack_bias",
    "skeptic_q": "Does RSI divergence add edge beyond our EW structure, or is it lagging noise?",
  },
  {
    "id": "supertrend_flip",
    "name": "Supertrend Flip / Trail",
    "category": "tv_oss",
    "keywords": ("supertrend", "super trend", "atr trailing stop", "trend flip"),
    "our_signal": "supertrend_aligned",
    "skeptic_q": "Is Supertrend alignment already captured in our TV confluence score?",
  },
  {
    "id": "chandelier_exit",
    "name": "Chandelier Exit Trail",
    "category": "tv_oss",
    "keywords": ("chandelier exit", "chandelier stop", "atr trailing stop"),
    "our_signal": "chandelier_aligned",
    "skeptic_q": "Does Chandelier add edge beyond Supertrend alone?",
  },
  {
    "id": "ttm_squeeze_release",
    "name": "TTM Squeeze Release",
    "category": "tv_oss",
    "keywords": ("ttm squeeze", "squeeze release", "momentum histogram", "lazybear squeeze"),
    "our_signal": "ttm_squeeze_release",
    "skeptic_q": "Does squeeze release timing align with EW wave-3 entries?",
  },
  {
    "id": "cvd_divergence",
    "name": "CVD Divergence",
    "category": "microstructure",
    "keywords": ("cvd", "cumulative volume delta", "volume delta", "order flow"),
    "our_signal": "cvd_divergence",
    "skeptic_q": "Does CVD divergence on OHLCV proxy match true tick CVD?",
  },
  {
    "id": "volume_profile_poc",
    "name": "Volume Profile POC",
    "category": "microstructure",
    "keywords": ("volume profile", "vpoc", "poc", "value area", "vah", "val"),
    "our_signal": "volume_profile_poc",
    "skeptic_q": "Does VP POC from OHLCV bins align with exchange footprint POC?",
  },
  {
    "id": "footprint_delta",
    "name": "Footprint Stacked Delta",
    "category": "microstructure",
    "keywords": ("footprint", "stacked delta", "bid ask delta", "order flow"),
    "our_signal": "footprint_aggression",
    "skeptic_q": "Is candle-split footprint proxy sufficient without tick data?",
  },
  {
    "id": "tpo_market_profile",
    "name": "TPO Market Profile",
    "category": "microstructure",
    "keywords": ("tpo", "market profile", "time price opportunity", "single prints"),
    "our_signal": "tpo_value_area",
    "skeptic_q": "Does bar-count TPO approximate session market profile?",
  },
  {
    "id": "anchored_vwap_tvwap",
    "name": "Anchored VWAP (TVWAP)",
    "category": "microstructure",
    "keywords": ("anchored vwap", "avwap", "tvwap", "session vwap"),
    "our_signal": "anchored_vwap_favorable",
    "skeptic_q": "Is swing-anchored VWAP the right anchor for crypto 24/7?",
  },
  {
    "id": "funding_squeeze",
    "name": "Funding Rate Squeeze",
    "category": "derivatives",
    "keywords": ("funding rate", "short squeeze", "long squeeze", "negative funding", "funding arb"),
    "our_signal": "funding_carry",
    "skeptic_q": "Does extreme funding predict reversal or continuation in our closed setups?",
  },
  {
    "id": "fear_greed_contrarian",
    "name": "Fear & Greed Contrarian",
    "category": "sentiment",
    "keywords": ("fear and greed", "extreme fear", "extreme greed", "buy fear sell greed"),
    "our_signal": "fear_greed_contrarian",
    "skeptic_q": "Do contrarian entries at fear/greed extremes beat our baseline WR?",
  },
  {
    "id": "golden_cross",
    "name": "Golden / Death Cross (EMA 50/200)",
    "category": "indicator",
    "keywords": ("golden cross", "death cross", "ema 50", "ema 200", "50/200 cross"),
    "our_signal": None,
    "skeptic_q": "Are EMA crosses late signals that conflict with EW impulse timing?",
  },
  {
    "id": "order_block_ict",
    "name": "ICT Order Blocks / FVG",
    "category": "structure",
    "keywords": ("order block", "fair value gap", "fvg", "ict", "liquidity sweep", "breaker block"),
    "our_signal": None,
    "skeptic_q": "Do ICT concepts overlap with our harmonic PRZ zones without added lift?",
  },
  {
    "id": "bb_squeeze",
    "name": "Bollinger Squeeze Breakout",
    "category": "tv_oss",
    "keywords": ("bollinger squeeze", "bb squeeze", "volatility squeeze", "keltner squeeze"),
    "our_signal": "bb_favorable",
    "skeptic_q": "Does squeeze breakout timing align with EW wave-3 entries?",
  },
  {
    "id": "liquidation_hunt",
    "name": "Liquidation Cascade / Stop Hunt",
    "category": "microstructure",
    "keywords": ("liquidation", "stop hunt", "liquidity grab", "cascade", "liq level"),
    "our_signal": "orderbook_imbalance",
    "skeptic_q": "Can we measure liquidation proximity reliably enough to size risk?",
  },
  {
    "id": "vwap_mean_reversion",
    "name": "VWAP Mean Reversion",
    "category": "indicator",
    "keywords": ("vwap", "mean reversion", "vwap bounce", "anchored vwap"),
    "our_signal": None,
    "skeptic_q": "Does VWAP reversion work on crypto 24/7 or only on equities?",
  },
  {
    "id": "macd_momentum",
    "name": "MACD Histogram Cross",
    "category": "indicator",
    "keywords": ("macd cross", "macd histogram", "macd divergence"),
    "our_signal": None,
    "skeptic_q": "Is MACD redundant with our multi-TF RSI stack?",
  },
  {
    "id": "wyckoff_accumulation",
    "name": "Wyckoff Accumulation / Distribution",
    "category": "structure",
    "keywords": ("wyckoff", "accumulation", "distribution", "spring", "upthrust"),
    "our_signal": "ew_impulse_valid",
    "skeptic_q": "Does Wyckoff map to our ending_diagonal / impulse structure labels?",
  },
  {
    "id": "grid_bot_dca",
    "name": "Grid / DCA Bot",
    "category": "strategy",
    "keywords": ("grid bot", "grid trading", "dca bot", "dollar cost average"),
    "our_signal": None,
    "skeptic_q": "Is grid/DCA a different regime than our directional EW setups?",
  },
)


def _social_source_urls() -> List[str]:
  raw = os.environ.get("EW_SOCIAL_SOURCES", "")
  if not raw.strip():
    return [
      "https://www.reddit.com/r/CryptoCurrency/hot.json?limit=15",
      "https://www.reddit.com/r/algotrading/hot.json?limit=10",
    ]
  return [u.strip() for u in raw.split(",") if u.strip()]


def _fetch_reddit_json(url: str) -> Optional[str]:
  """Reddit JSON endpoints — no HTML scrape needed."""
  from gateway.web_intel import _fetch_json

  data = _fetch_json(url, host="reddit.com")
  if not data or data.get("error"):
    return None
  posts = data.get("data", {}).get("children") or []
  parts = []
  for p in posts[:20]:
    d = p.get("data") or {}
    title = d.get("title", "")
    selftext = (d.get("selftext") or "")[:500]
    parts.append(f"{title} {selftext}")
  return " ".join(parts).lower()


def _gather_social_text() -> Tuple[str, List[str]]:
  """Aggregate text from configured social/forum sources."""
  combined: List[str] = []
  sources_used: List[str] = []

  for url in _social_source_urls():
    text = ""
    if "reddit.com" in url and (url.endswith(".json") or "/.json" in url):
      text = _fetch_reddit_json(url) or ""
    else:
      page = scrape_page_text(url, max_chars=3000)
      if page.get("available"):
        text = (page.get("text") or "").lower()
    if text:
      combined.append(text)
      sources_used.append(url)

  return " ".join(combined), sources_used


def scan_forum_mentions(text: str) -> List[dict]:
  """Match catalog strategies against aggregated social text."""
  text_l = text.lower()
  hits: List[dict] = []
  for strat in FORUM_STRATEGY_CATALOG:
    count = 0
    matched_kw: List[str] = []
    for kw in strat["keywords"]:
      n = len(re.findall(re.escape(kw), text_l))
      if n:
        count += n
        matched_kw.append(kw)
    if count:
      hits.append({
        **{k: strat[k] for k in ("id", "name", "category", "our_signal", "skeptic_q")},
        "mention_count": count,
        "matched_keywords": matched_kw,
        "social_heat": min(100, count * 8),
      })
  hits.sort(key=lambda x: -x["mention_count"])
  return hits


def cross_reference_impact(candidates: List[dict], impact: Optional[dict] = None) -> List[dict]:
  """Score social candidates against our measured outcome lift."""
  if impact is None:
    try:
      from engine.impact_discovery import load_impact_report

      impact = load_impact_report()
    except Exception:
      impact = {}

  discovery = impact.get("discovery") or {}
  baseline = discovery.get("baseline_wr")
  boosts = {f["factor"]: f for f in discovery.get("top_boosts", [])}
  sources = {s["id"]: s for s in (impact.get("data_sources") or [])}

  enriched = []
  for c in candidates:
    our_id = c.get("our_signal")
    measured_lift = None
    measured_evidence = "not yet measured in our data"
    if our_id and our_id in sources:
      measured_lift = sources[our_id].get("inferred_lift")
      measured_evidence = sources[our_id].get("evidence", "")
    for f in discovery.get("factors", []):
      factor = f.get("factor", "")
      if our_id and our_id.replace("_", "") in factor.replace("_", "").replace(":", ""):
        measured_lift = f.get("lift_vs_baseline")
        measured_evidence = f"measured n={f.get('n')}"
        break

    social_heat = c.get("social_heat", 0)
    if measured_lift is not None and measured_lift > 0.05:
      validation_prior = "likely_valid"
    elif measured_lift is not None and measured_lift < -0.05:
      validation_prior = "likely_noise"
    elif social_heat >= 40:
      validation_prior = "needs_validation"
    else:
      validation_prior = "low_priority"

    enriched.append({
      **c,
      "measured_lift": measured_lift,
      "measured_evidence": measured_evidence,
      "baseline_wr": baseline,
      "validation_prior": validation_prior,
    })
  enriched.sort(key=lambda x: (
    {"likely_valid": 0, "needs_validation": 1, "low_priority": 2, "likely_noise": 3}.get(x["validation_prior"], 4),
    -x.get("social_heat", 0),
  ))
  return enriched


def build_social_intel(symbol: str = "") -> Dict[str, Any]:
  """
  Discover forum-popular strategies and cross-reference with our measured data.
  Returns candidates ranked for executive validation.
  """
  if not social_intel_enabled():
    return {"available": False, "reason": "EW_SOCIAL_INTEL disabled"}

  text, sources = _gather_social_text()
  if not text:
    # Offline fallback — still surface catalog for questioning
    candidates = [
      {
        **{k: s[k] for k in ("id", "name", "category", "our_signal", "skeptic_q")},
        "mention_count": 0,
        "matched_keywords": [],
        "social_heat": 0,
        "offline_seed": True,
      }
      for s in FORUM_STRATEGY_CATALOG[:6]
    ]
    return {
      "available": True,
      "symbol": symbol,
      "sources": sources,
      "candidates": cross_reference_impact(candidates),
      "social_text_chars": 0,
      "mode": "offline_catalog",
    }

  raw_hits = scan_forum_mentions(text)
  candidates = cross_reference_impact(raw_hits)
  signals = [f"social:{c['name']} (heat {c.get('social_heat', 0)})" for c in candidates[:3]]

  return {
    "available": True,
    "symbol": symbol,
    "sources": sources,
    "candidates": candidates,
    "social_text_chars": len(text),
    "signals": signals,
    "mode": "live_scan",
  }
