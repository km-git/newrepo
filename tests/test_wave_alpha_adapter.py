"""Tests for wave-alpha adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.wave_alpha_adapter import symbol_to_wave_alpha_ticker, scan_wave_alpha


def test_symbol_to_wave_alpha_ticker():
  assert symbol_to_wave_alpha_ticker("BTC/USDT") == "BTC-USD"
  assert symbol_to_wave_alpha_ticker("ETH/USDT") == "ETH-USD"
  assert symbol_to_wave_alpha_ticker("SOL/USDC") == "SOL-USD"


@patch("core.wave_alpha_adapter._package_available", return_value=True)
@patch("wave_alpha.web.deps.analyze")
def test_scan_wave_alpha_from_signal(mock_analyze, _avail):
  sig = MagicMock()
  sig.direction = "short"
  sig.confidence = 0.82
  sig.count_pattern = "zigzag"
  sig.wave_label = "C"

  result = MagicMock()
  result.signals = [sig]
  result.ranked_daily = []
  result.coherence = MagicMock(score=0.71)
  mock_analyze.return_value = result

  out = scan_wave_alpha("ETH/USDT")
  assert out["available"]
  assert out["direction"] == "BEAR"
  assert out["confidence"] == 0.82
  assert "zigzag" in out["detail"]
  mock_analyze.assert_called_once()
  args = mock_analyze.call_args[0]
  assert args[0] == "ETH-USD"


def test_scan_wave_alpha_not_installed():
  with patch("core.wave_alpha_adapter._package_available", return_value=False):
    out = scan_wave_alpha("BTC/USDT")
    assert not out["available"]
