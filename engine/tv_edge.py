"""TradingView OSS edge layer — institutional SMC + QuanTAlib enhanced indicators."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from core.institutional_edge import build_institutional_matrix
from core.tv_enhanced import compute_enhanced_indicators, detect_oscillator_divergence, score_enhanced_confluence

DEFAULT_EDGE_TFS = ["15m", "1h", "4h", "1d", "1w"]


def build_smc_matrix(
  data: Dict[str, pd.DataFrame],
  tfs: Optional[List[str]] = None,
  direction: str = "LONG",
  exchange=None,
  symbol: str = "",
) -> dict:
  """Institutional SMC matrix via smartmoneyconcepts library."""
  inst = build_institutional_matrix(
    data, direction, tfs=tfs or DEFAULT_EDGE_TFS, exchange=exchange, symbol=symbol,
  )
  by_tf = inst.get("by_tf", {})
  valid = sum(1 for v in by_tf.values() if v.get("entry_signal"))
  partial = sum(1 for v in by_tf.values() if v.get("partial_confluence", 0) >= 1)
  return {
    "by_tf": by_tf,
    "valid_count": valid,
    "partial_count": partial,
    "coverage_pct": round(100 * partial / max(len(by_tf), 1), 1),
    "institutional": inst,
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
  exchange=None,
) -> dict:
  """
  Aggregate institutional edge for a symbol (Phases 1–5).
  Returns tokens usable by indicator calibration + readiness SMC path.
  """
  inst = build_institutional_matrix(
    data, direction, tfs=["15m", "1h", "4h", "1d"], exchange=exchange, symbol=symbol,
  )
  enhanced = build_enhanced_matrix(data)
  primary_inst = inst.get("by_tf", {}).get(primary_tf, inst.get("by_tf", {}).get("1h", {}))
  primary_enh = enhanced["by_tf"].get(primary_tf, {})

  enh_score, enh_tags = score_enhanced_confluence(
    primary_enh, direction, primary_enh.get("divergence")
  )
  smc_score = int(inst.get("institutional_score", 0))
  smc_tags = list(inst.get("tags", []))

  aligned_tfs = [
    tf for tf, s in inst.get("by_tf", {}).items()
    if s.get("status") == "ok" and s.get("score", 0) >= 35
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
    "smc_valid": bool(inst.get("entry_signal")) or inst.get("entry_probe") or inst.get("entry_grade") in ("A", "B"),
    "smc_partial": inst.get("confluence_count", 0) >= 1,
    "smc_aligned": True,
    "smc_structure": primary_inst.get("structure_event", "none"),
    "structure_bias": "BULL" if direction in ("LONG", "BULL") else "BEAR",
    "aligned_tfs": aligned_tfs,
    "tags": all_tags,
    "tokens": [(t, 15) for t in all_tags[:8]],
    "smc_matrix": {"by_tf": inst.get("by_tf", {}), "institutional": inst},
    "enhanced_matrix": enhanced,
    "institutional": inst,
    "primary_tf": primary_tf,
    "entry_signal": inst.get("entry_signal", False),
    "entry_probe": inst.get("entry_probe", False),
    "entry_grade": inst.get("entry_grade", "D"),
  }


TV_TOKEN_MAP = {
  "SMC bos bull": "SMC BOS bull",
  "SMC choch bull": "SMC CHoCH bull",
  "SMC bos bear": "SMC BOS bear",
  "SMC choch bear": "SMC CHoCH bear",
  "in bullish OB": "in bullish OB",
  "in bearish OB": "in bearish OB",
  "bullish FVG zone": "bullish FVG zone",
  "bearish FVG zone": "bearish FVG zone",
  "liquidity sweep": "liquidity sweep",
  "liquidity sweep (EQL)": "liquidity sweep EQL",
  "liquidity sweep (EQH)": "liquidity sweep EQH",
  "equal highs": "equal highs",
  "equal lows": "equal lows",
  "MSB z-score pass": "MSB z-score pass",
  "MSB z-score weak": "MSB z-score weak",
  "CVD bullish divergence": "CVD bullish divergence",
  "CVD bearish divergence": "CVD bearish divergence",
  "at volume POC": "at volume POC",
  "VP filter pass": "VP filter pass",
  "HA bull + ROC up": "HA bull ROC up",
  "HA bear + ROC down": "HA bear ROC down",
  "OBI bid pressure": "OBI bid pressure",
  "OBI ask pressure": "OBI ask pressure",
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
    low = tag.lower()
    matched = False
    for prefix, token in TV_TOKEN_MAP.items():
      if low.startswith(prefix.lower()) or low == prefix.lower():
        out.append(token)
        matched = True
        break
    if not matched and tag.lower().startswith("smc "):
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

  if not indicators.get("calibrated") and tv_edge:
    bonus = min(25, int(tv_edge.get("edge_score", 0) * 0.25))
    if bonus:
      indicators["score"] = min(100, indicators.get("score", 0) + bonus)
      indicators["aligned"] = indicators["score"] >= indicators.get("threshold", 58)
      indicators["signals"] = list(indicators.get("signals", [])) + tv_edge.get("tags", [])[:3]

  return indicators
