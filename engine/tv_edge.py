"""TradingView OSS edge layer — SMC + QuanTAlib enhanced indicators."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from core.smc_structure import analyze_smc, smc_aligns_direction
from core.tv_enhanced import compute_enhanced_indicators, detect_oscillator_divergence, score_enhanced_confluence

DEFAULT_EDGE_TFS = ["15m", "1h", "4h", "1d", "1w"]


def build_smc_matrix(data: Dict[str, pd.DataFrame], tfs: Optional[List[str]] = None) -> dict:
  tfs = tfs or DEFAULT_EDGE_TFS
  matrix = {}
  for tf in tfs:
    df = data.get(tf)
    if df is None or len(df) < 30:
      matrix[tf] = {"status": "no_data"}
      continue
    pivot = 5 if tf in ("15m", "1h") else 7
    matrix[tf] = analyze_smc(df, pivot_len=pivot, ms_pivot_len=pivot + 2)
  valid = sum(1 for v in matrix.values() if v.get("smc_valid"))
  partial = sum(1 for v in matrix.values() if v.get("smc_partial"))
  return {
    "by_tf": matrix,
    "valid_count": valid,
    "partial_count": partial,
    "coverage_pct": round(100 * valid / max(len(tfs), 1), 1),
  }


def build_enhanced_matrix(data: Dict[str, pd.DataFrame], tfs: Optional[List[str]] = None) -> dict:
  tfs = tfs or ["15m", "1h", "4h", "1d"]
  matrix = {}
  for tf in tfs:
    df = data.get(tf)
    if df is None or len(df) < 30:
      matrix[tf] = {"status": "no_data"}
      continue
    enh = compute_enhanced_indicators(df)
    div = detect_oscillator_divergence(df)
    enh["divergence"] = div
    matrix[tf] = enh
  return {"by_tf": matrix}


def build_tv_edge_layer(
  symbol: str,
  data: Dict[str, pd.DataFrame],
  direction: str,
  primary_tf: str = "1h",
) -> dict:
  """
  Aggregate TV OSS edge for a symbol.
  Returns tokens usable by indicator calibration + readiness SMC path.
  """
  smc = build_smc_matrix(data)
  enhanced = build_enhanced_matrix(data)
  primary_smc = smc["by_tf"].get(primary_tf, {})
  primary_enh = enhanced["by_tf"].get(primary_tf, {})

  enh_score, enh_tags = score_enhanced_confluence(
    primary_enh, direction, primary_enh.get("divergence")
  )
  smc_score = int(primary_smc.get("smc_score", 0))
  smc_tags = list(primary_smc.get("tags", []))

  # Multi-TF SMC alignment bonus
  aligned_tfs = [
    tf for tf, s in smc["by_tf"].items()
    if s.get("status") == "ok" and smc_aligns_direction(s, direction)
  ]
  mtf_bonus = min(15, len(aligned_tfs) * 4)

  edge_score = min(100, smc_score + enh_score + mtf_bonus)
  all_tags = smc_tags + enh_tags
  if len(aligned_tfs) >= 2:
    all_tags.append(f"SMC MTF align {len(aligned_tfs)} TFs")

  return {
    "symbol": symbol,
    "edge_score": edge_score,
    "smc_score": smc_score,
    "enhanced_score": enh_score,
    "mtf_bonus": mtf_bonus,
    "smc_valid": bool(primary_smc.get("smc_valid")),
    "smc_partial": bool(primary_smc.get("smc_partial")),
    "smc_aligned": smc_aligns_direction(primary_smc, direction),
    "smc_structure": primary_smc.get("last_event", "none"),
    "structure_bias": primary_smc.get("structure_bias", "NEUTRAL"),
    "aligned_tfs": aligned_tfs,
    "tags": all_tags,
    "tokens": [(t, 15) for t in all_tags[:8]],
    "smc_matrix": smc,
    "enhanced_matrix": enhanced,
    "primary_tf": primary_tf,
  }


# Maps TV edge tag prefixes → calibration token names
TV_TOKEN_MAP = {
  "SMC BOS bull": "SMC BOS bull",
  "SMC CHoCH bull": "SMC CHoCH bull",
  "SMC BOS bear": "SMC BOS bear",
  "SMC CHoCH bear": "SMC CHoCH bear",
  "in bullish OB": "in bullish OB",
  "in bearish OB": "in bearish OB",
  "bullish FVG zone": "bullish FVG zone",
  "bearish FVG zone": "bearish FVG zone",
  "ADX": "ADX trend strong",
  "above SuperTrend": "above SuperTrend",
  "below SuperTrend": "below SuperTrend",
  "Williams %R oversold": "Williams %R oversold",
  "Williams %R overbought": "Williams %R overbought",
  "RSI bullish divergence": "RSI bullish divergence",
  "RSI bearish divergence": "RSI bearish divergence",
  "momentum z=": "momentum z-score",
  "SMC MTF align": "SMC MTF align",
}


def normalize_tv_tokens(tags: List[str]) -> List[str]:
  out: List[str] = []
  for tag in tags:
    matched = False
    for prefix, token in TV_TOKEN_MAP.items():
      if tag.startswith(prefix) or tag == prefix:
        out.append(token)
        matched = True
        break
    if not matched and tag.startswith("SMC "):
      out.append(tag.split("(")[0].strip())
  return list(dict.fromkeys(out))


def merge_tv_tokens_into_indicators(
  indicators: dict,
  tv_edge: dict,
  market_tools: Optional[dict] = None,
) -> dict:
  """Add TV edge + market microstructure tokens to indicator score."""
  if not tv_edge and not market_tools:
    return indicators

  from engine.indicator_calibration import apply_extra_calibration_tokens

  indicators = dict(indicators)
  extra = normalize_tv_tokens(tv_edge.get("tags", []) if tv_edge else [])
  if market_tools:
    extra.extend(market_tools.get("calibration_tokens", []))
  extra = list(dict.fromkeys(extra))

  indicators["tv_edge_score"] = tv_edge.get("edge_score", 0) if tv_edge else 0
  indicators["tv_edge_tags"] = tv_edge.get("tags", []) if tv_edge else []
  indicators["market_tokens"] = market_tools.get("calibration_tokens", []) if market_tools else []

  if extra:
    indicators = apply_extra_calibration_tokens(indicators, extra)

  # Uncalibrated fallback boost
  if not indicators.get("calibrated") and tv_edge:
    bonus = min(25, int(tv_edge.get("edge_score", 0) * 0.25))
    if bonus:
      indicators["score"] = min(100, indicators.get("score", 0) + bonus)
      indicators["aligned"] = indicators["score"] >= indicators.get("threshold", 58)
      indicators["signals"] = list(indicators.get("signals", [])) + tv_edge.get("tags", [])[:3]

  return indicators
