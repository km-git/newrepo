"""
Self-challenge audit — question missing free data, TV OSS, GitHub tools, Python libs.

Runs automatically on autonomous ticks and surfaces gaps for executive improvement.
"""

from __future__ import annotations

import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

AUDIT_PATH = Path(os.environ.get("EW_TOOL_AUDIT_STATE", "output/system/tool_resource_audit.json"))

# Registry of what we expect to be wired
FREE_DATA_SOURCES = [
  {"id": "fear_greed", "module": "gateway.web_intel", "fn": "fear_greed_index"},
  {"id": "coingecko_global", "module": "gateway.web_intel", "fn": "coingecko_global"},
  {"id": "coingecko_coin", "module": "gateway.web_intel", "fn": "coingecko_coin_stats"},
  {"id": "defillama_stablecoins", "module": "gateway.web_intel", "fn": "defillama_stablecoins"},
  {"id": "defillama_tvl", "module": "gateway.web_intel", "fn": "defillama_total_tvl"},
  {"id": "funding_cross", "module": "gateway.web_intel", "fn": "funding_cross_check"},
  {"id": "oi_cross", "module": "gateway.web_intel", "fn": "oi_cross_check"},
  {"id": "long_short_ratio", "module": "gateway.web_intel", "fn": "binance_long_short_ratio"},
  {"id": "taker_ratio", "module": "gateway.web_intel", "fn": "binance_taker_ratio"},
  {"id": "spot_perp_basis", "module": "gateway.web_intel", "fn": "spot_perp_basis"},
  {"id": "liquidations", "module": "gateway.web_intel", "fn": "binance_recent_liquidations"},
  {"id": "macro_tradfi", "module": "gateway.web_intel", "fn": "macro_tradfi_snapshot"},
  {"id": "ws_ticker", "module": "gateway.ws_hub", "fn": "get_ws_hub"},
  {"id": "social_intel", "module": "gateway.social_intel", "fn": "build_social_intel"},
]

TV_OSS_REQUIRED = [
  "supertrend", "chandelier", "hull_ma", "bollinger", "ttm_squeeze", "adx", "rsi", "vwap",
]

TV_OSS_EXPLORATION = [
  "cmf", "williams_r", "aroon", "stoch_rsi", "obv_trend", "wavetrend", "keltner_break", "fisher",
]

GITHUB_TOOLS = [
  {"id": "elliott_wave_analyzer", "path": "core/ewa_adapter.py"},
  {"id": "python_taew", "path": "core/taew_adapter.py"},
  {"id": "pyharmonics", "path": "core/harmonic.py"},
]

PYTHON_LIBS = [
  "ccxt", "pandas", "numpy", "yfinance", "websockets", "diskcache", "zstandard",
  "tiktoken", "numba", "pyharmonics",
]

# Known gaps to keep challenging (update as we integrate)
KNOWN_GAPS = [
  {"id": "ws_l2_depth", "priority": "high", "note": "WS books5/trades for true CVD — gateway/ws_hub.py"},
  {"id": "deribit_iv_skew", "priority": "medium", "note": "BTC options IV skew — gateway/derivatives_intel.py"},
  {"id": "coinglass_liq_heatmap", "priority": "medium", "note": "Aggregated liq levels beyond Binance force orders"},
  {"id": "etf_flows", "priority": "low", "note": "BTC ETF flow data for macro regime"},
]


def audit_enabled() -> bool:
  return os.environ.get("EW_TOOL_AUDIT", "1").lower() not in ("0", "false", "no")


def _fn_exists(module: str, fn: str) -> bool:
  try:
    mod = importlib.import_module(module)
    return callable(getattr(mod, fn, None))
  except Exception:
    return False


def _path_exists(rel: str) -> bool:
  return (Path(__file__).resolve().parents[1] / rel).exists()


def _lib_installed(name: str) -> bool:
  try:
    importlib.import_module(name)
    return True
  except ImportError:
    return False


def _check_tv_oss() -> Dict[str, Any]:
  from core.tv_indicators import TV_OSS_CATALOG, _EXPLORATION_FN, compute_exploration_signals
  import pandas as pd
  import numpy as np

  active = [c["id"] for c in TV_OSS_CATALOG]
  missing_active = [i for i in TV_OSS_REQUIRED if i not in active]
  exploration_impl = list(_EXPLORATION_FN.keys())
  missing_explore = [i for i in TV_OSS_EXPLORATION if i not in exploration_impl]

  # Smoke test exploration compute
  n = 80
  rng = np.random.default_rng(42)
  close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
  df = pd.DataFrame({
    "Open": close, "High": close * 1.01, "Low": close * 0.99,
    "Close": close, "Volume": rng.uniform(1e3, 1e4, n),
  })
  explore_ok = sum(1 for v in compute_exploration_signals(df).values() if v.get("available"))

  return {
    "active_stack": active,
    "missing_active": missing_active,
    "exploration_implemented": exploration_impl,
    "missing_exploration": missing_explore,
    "exploration_smoke_ok": explore_ok,
  }


def run_tool_resource_audit(*, persist: bool = True) -> Dict[str, Any]:
  """
  Self-challenge: are we missing any key free sources, TV OSS, GitHub tools, or libs?
  """
  if not audit_enabled():
    return {"skipped": True, "reason": "EW_TOOL_AUDIT disabled"}

  data_sources = []
  for src in FREE_DATA_SOURCES:
    data_sources.append({
      **src,
      "wired": _fn_exists(src["module"], src["fn"]),
    })

  github = []
  for tool in GITHUB_TOOLS:
    github.append({**tool, "present": _path_exists(tool["path"])})

  libs = [{"name": n, "installed": _lib_installed(n)} for n in PYTHON_LIBS]

  tv = _check_tv_oss()
  gaps = list(KNOWN_GAPS)

  unwired = [s["id"] for s in data_sources if not s["wired"]]
  if unwired:
    gaps.append({
      "id": "unwired_data_sources",
      "priority": "high",
      "note": f"Functions missing: {unwired}",
    })
  if tv.get("missing_exploration"):
    gaps.append({
      "id": "tv_oss_exploration_gaps",
      "priority": "medium",
      "note": f"Not implemented: {tv['missing_exploration']}",
    })

  result = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "challenge": "Are we missing free data, TV OSS, GitHub tools, or Python libs?",
    "free_data_sources": data_sources,
    "tv_oss": tv,
    "github_tools": github,
    "python_libs": libs,
    "known_gaps": gaps,
    "summary": {
      "data_wired": sum(1 for s in data_sources if s["wired"]),
      "data_total": len(data_sources),
      "github_present": sum(1 for g in github if g["present"]),
      "libs_installed": sum(1 for l in libs if l["installed"]),
      "open_gaps": len(gaps),
    },
  }

  if persist:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

  return result


def load_tool_audit() -> dict:
  if not AUDIT_PATH.exists():
    return {}
  try:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}
