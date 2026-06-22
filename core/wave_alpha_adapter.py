"""wave-alpha (PyPI) adapter — rule-validated EW thesis vote for Sentinel stack."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

_WAVE_ALPHA_AVAILABLE: Optional[bool] = None


def _package_available() -> bool:
  global _WAVE_ALPHA_AVAILABLE
  if _WAVE_ALPHA_AVAILABLE is not None:
    return _WAVE_ALPHA_AVAILABLE
  try:
    import wave_alpha  # noqa: F401
    from wave_alpha.web.deps import analyze  # noqa: F401
    _WAVE_ALPHA_AVAILABLE = True
  except ImportError:
    _WAVE_ALPHA_AVAILABLE = False
  return _WAVE_ALPHA_AVAILABLE


def symbol_to_wave_alpha_ticker(symbol: str) -> str:
  """
  Map exchange pair to yfinance-style ticker for wave-alpha.
  BTC/USDT → BTC-USD, AAPL/USDT → AAPL (stocks).
  """
  base = symbol.split("/")[0].upper()
  quote = symbol.split("/")[1].upper() if "/" in symbol else "USDT"
  if quote in ("USDT", "USD", "USDC", "BUSD"):
    # Crypto on Yahoo: BASE-USD
    if base in ("XBT",):
      return "BTC-USD"
    return f"{base}-USD"
  return base


def scan_wave_alpha(symbol: str, as_of: Optional[date] = None) -> dict:
  """
  Run wave-alpha analyze (LLM disabled) and return directional vote.
  Uses top TradeSignal by confidence; falls back to ranked_daily top count.
  """
  if not _package_available():
    return {"available": False, "reason": "wave-alpha not installed"}

  from wave_alpha.llm.modes import LLMMode
  from wave_alpha.web.deps import analyze

  ticker = symbol_to_wave_alpha_ticker(symbol)
  as_of = as_of or datetime.now(timezone.utc).date()

  try:
    result = analyze(ticker, as_of, llm_mode=LLMMode.DISABLED)
  except Exception as e:
    return {"available": False, "error": str(e), "ticker": ticker}

  direction = None
  confidence = 0.0
  pattern = ""
  wave_label = ""
  coherence = None

  if result.signals:
    best = max(result.signals, key=lambda s: s.confidence)
    direction = "BULL" if best.direction == "long" else "BEAR"
    confidence = float(best.confidence)
    pattern = best.count_pattern
    wave_label = best.wave_label
  elif result.ranked_daily:
    rc = result.ranked_daily[0]
    # Infer from wave pattern / pivot structure when no trade signal derived
    confidence = float(rc.final_score)
    pattern = getattr(rc.count, "pattern", "") or str(getattr(rc.count, "template", ""))
    # Use coherence bias if present
    if result.coherence and result.coherence.score >= 0.5:
      coherence = float(result.coherence.score)

  if direction is None:
    return {
      "available": False,
      "reason": "no_signals",
      "ticker": ticker,
      "ranked_counts": len(result.ranked_daily),
    }

  coh_score = float(result.coherence.score) if result.coherence else coherence
  detail = f"wave-alpha {pattern} wave {wave_label} conf={confidence:.2f}"
  if coh_score is not None:
    detail += f" coherence={coh_score:.2f}"

  return {
    "available": True,
    "source": "wave-alpha>=0.14",
    "ticker": ticker,
    "direction": direction,
    "confidence": min(confidence, 0.95),
    "pattern": pattern,
    "wave_label": wave_label,
    "coherence_score": coh_score,
    "signal_count": len(result.signals),
    "detail": detail,
  }
