"""
Resource gap audit — challenge ourselves: are we missing free data, TV OSS, GitHub tools, or libs?

Runs on every improvement cycle and autonomous tick. Produces prioritized gaps + self-challenge questions.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

Impact = Literal["critical", "high", "medium", "low"]
Status = Literal["integrated", "partial", "missing", "candidate"]

AUDIT_PATH = Path(os.environ.get("EW_GAP_AUDIT_STATE", "output/system/resource_gap_audit.json"))


def gap_audit_enabled() -> bool:
  return os.environ.get("EW_GAP_AUDIT", "1").lower() not in ("0", "false", "no")


def _importable(module: str) -> bool:
  try:
    importlib.import_module(module)
    return True
  except ImportError:
    return False


def _cli_available(cmd: str) -> bool:
  return shutil.which(cmd) is not None


def _env_on(name: str, default: str = "1") -> bool:
  return os.environ.get(name, default).lower() not in ("0", "false", "no")


def _tv_catalog_counts() -> Dict[str, int]:
  counts = {"active": 0, "candidates": 0, "microstructure": 0, "cycles": 0}
  try:
    from core.tv_indicators import TV_OSS_CATALOG, TV_OSS_CANDIDATES

    counts["active"] = len(TV_OSS_CATALOG)
    counts["candidates"] = len(TV_OSS_CANDIDATES)
  except ImportError:
    pass
  try:
    from core.tv_microstructure import TV_MICROSTRUCTURE_CATALOG

    counts["microstructure"] = len(TV_MICROSTRUCTURE_CATALOG)
  except ImportError:
    pass
  try:
    from core.tv_cycles import TV_CYCLE_CATALOG

    counts["cycles"] = len(TV_CYCLE_CATALOG)
  except ImportError:
    pass
  return counts


# Curated watchlist — high-impact items we should always question
WATCHLIST: Tuple[Dict[str, Any], ...] = (
  # Free data
  {"id": "fear_greed", "category": "free_data", "impact": "high",
   "integrated_in": "gateway/web_intel.py", "challenge": "Are extreme fear/greed thresholds tuned per asset class?"},
  {"id": "coingecko_global", "category": "free_data", "impact": "medium",
   "integrated_in": "gateway/web_intel.py", "challenge": "Do we use BTC dominance + stablecoin mcap for risk-off detection?"},
  {"id": "binance_funding", "category": "free_data", "impact": "high",
   "integrated_in": "gateway/web_intel.py", "challenge": "OKX funding fallback when Binance 451 — verify both paths?"},
  {"id": "ws_orderbook", "category": "free_data", "impact": "high",
   "integrated_in": "gateway/ws_hub.py", "challenge": "Is WS imbalance used on every executive decision or only when EW_WS_ENABLED=1?"},
  {"id": "reddit_social", "category": "free_data", "impact": "medium",
   "integrated_in": "gateway/social_intel.py", "challenge": "Reddit-only — should we add CryptoPanic, LunarCrush free tier, or GitHub trending?"},
  {"id": "open_interest", "category": "free_data", "impact": "high",
   "integrated_in": "gateway/web_intel.py#okx_open_interest", "challenge": "OI trend delta not tracked — rising OI into breakout?"},
  {"id": "onchain_flow", "category": "free_data", "impact": "medium",
   "integrated_in": None, "challenge": "No exchange inflow/outflow — are whale moves invisible?"},
  {"id": "economic_calendar", "category": "free_data", "impact": "medium",
   "integrated_in": None, "challenge": "FOMC/CPI events can invalidate EW counts — do we gate entries?"},
  # TV OSS
  {"id": "tv_supertrend", "category": "tv_oss", "impact": "high",
   "integrated_in": "core/tv_indicators.py", "challenge": "Is Supertrend ATR multiplier optimized per TF?"},
  {"id": "tv_cvd_footprint", "category": "tv_oss", "impact": "critical",
   "integrated_in": "core/tv_microstructure.py", "challenge": "CVD uses OHLCV proxy — do we need tick/trade data for accuracy?"},
  {"id": "tv_market_structure", "category": "tv_oss", "impact": "high",
   "integrated_in": "core/tv_market_structure.py", "challenge": "BOS/CHoCH in board scoring — validate lift via impact discovery?"},
  {"id": "tv_wavetrend", "category": "tv_oss", "impact": "medium",
   "integrated_in": "core/tv_indicators.py#candidates", "challenge": "WaveTrend in candidates — has impact discovery validated lift?"},
  {"id": "tv_ichimoku", "category": "tv_oss", "impact": "medium",
   "integrated_in": None, "challenge": "Ichimoku cloud absent — missing Asian-session trend filter?"},
  {"id": "tv_volume_profile", "category": "tv_oss", "impact": "high",
   "integrated_in": "core/tv_microstructure.py", "challenge": "VP POC used in impact factors — is it in executive board scoring?"},
  # GitHub / OSS tools
  {"id": "gh_elliott_libs", "category": "github", "impact": "critical",
   "integrated_in": "libs/pyharmonics,ElliottWaveAnalyzer,python-taew", "challenge": "Are all three EW libs consensus-weighted equally?"},
  {"id": "gh_ccxt", "category": "github", "impact": "critical",
   "integrated_in": "fetchers/ccxt_fetcher.py", "challenge": "Exchange fallback chain complete — any missing liquid venues?"},
  {"id": "gh_tv_pine_ports", "category": "github", "impact": "high",
   "integrated_in": None, "challenge": "No auto-discovery of TradingView OSS Pine repos — manual catalog only?"},
  {"id": "gh_luxalgo", "category": "github", "impact": "medium",
   "integrated_in": None, "challenge": "LuxAlgo SMC indicators popular — evaluate open ports vs license?"},
  {"id": "gh_context", "category": "github", "impact": "low",
   "integrated_in": "tools/github_context.py", "challenge": "GitHub context not in trading loop — only architect/PR?"},
  # Python libraries
  {"id": "lib_pandas_ta", "category": "python_lib", "impact": "medium",
   "integrated_in": None, "challenge": "pandas-ta has 130+ indicators — are we reinventing wheels?"},
  {"id": "lib_ta_lib", "category": "python_lib", "impact": "low",
   "integrated_in": None, "challenge": "TA-Lib C dep heavy — justified vs pure-pandas TV ports?"},
  {"id": "lib_vectorbt", "category": "python_lib", "impact": "medium",
   "integrated_in": None, "challenge": "No vectorized backtest — autoresearch env-only, not strategy code?"},
  {"id": "lib_token_savers", "category": "python_lib", "impact": "high",
   "integrated_in": "engine/token_saver_registry.py", "challenge": "All token savers installed? Run --llm-savers."},
  {"id": "lib_websockets", "category": "python_lib", "impact": "high",
   "integrated_in": "gateway/ws_hub.py", "challenge": "websockets package required for live imbalance."},
  # Self-learning
  {"id": "loop_impact_discovery", "category": "self_learning", "impact": "critical",
   "integrated_in": "engine/impact_discovery.py", "challenge": "Enough closed setups for lift stats — min sample met?"},
  {"id": "loop_tv_oss_discovery", "category": "self_learning", "impact": "high",
   "integrated_in": "engine/tv_oss_discovery.py", "challenge": "Candidates promoted to active stack via measured lift?"},
  {"id": "loop_autoresearch", "category": "self_learning", "impact": "high",
   "integrated_in": "engine/autoresearch.py", "challenge": "Autoresearch promotes env vars only — code experiments missing?"},
  {"id": "loop_okf_brain", "category": "self_learning", "impact": "medium",
   "integrated_in": "engine/okf_brain.py", "challenge": "OKF lesson sprawl — dedup/compaction needed?"},
  {"id": "loop_gap_audit", "category": "self_learning", "impact": "high",
   "integrated_in": "engine/resource_gap_audit.py", "challenge": "This audit runs each cycle — are top gaps acted on?"},
)


def _resolve_status(item: dict) -> Status:
  integrated = item.get("integrated_in")
  if not integrated:
    return "missing"
  cat = item.get("category", "")
  if cat == "python_lib":
    mod_map = {
      "lib_websockets": "websockets",
      "lib_pandas_ta": "pandas_ta",
      "lib_ta_lib": "talib",
      "lib_vectorbt": "vectorbt",
      "lib_token_savers": "tiktoken",
    }
    mod = mod_map.get(item["id"])
    if mod:
      return "integrated" if _importable(mod) else "partial"
    if item["id"] == "lib_token_savers":
      try:
        from engine.token_saver_registry import library_status

        rows = library_status()
        installed = sum(1 for r in rows if r.get("installed"))
        if installed >= len(rows) - 1:
          return "integrated"
        if installed > 0:
          return "partial"
        return "missing"
      except ImportError:
        return "partial"
  if cat == "github" and item["id"] == "gh_context":
    return "integrated" if _env_on("EW_OKF_BRAIN") else "partial"
  if cat == "free_data":
    checks = {
      "fear_greed": _env_on("EW_WEB_INTEL"),
      "coingecko_global": _env_on("EW_WEB_INTEL"),
      "binance_funding": _env_on("EW_WEB_INTEL"),
      "ws_orderbook": _env_on("EW_WS_ENABLED"),
      "reddit_social": _env_on("EW_SOCIAL_INTEL"),
    }
    if item["id"] in checks:
      return "integrated" if checks[item["id"]] else "partial"
  if cat == "tv_oss" and item.get("integrated_in"):
    return "integrated"
  if cat == "self_learning":
    env_map = {
      "loop_impact_discovery": "EW_IMPACT_DISCOVERY",
      "loop_tv_oss_discovery": "EW_TV_OSS_EXPLORE",
      "loop_autoresearch": "EW_AUTORESEARCH",
      "loop_okf_brain": "EW_OKF_BRAIN",
      "loop_gap_audit": "EW_GAP_AUDIT",
    }
    env = env_map.get(item["id"])
    if env:
      return "integrated" if _env_on(env) else "partial"
  return "integrated" if integrated else "missing"


def _impact_rank(impact: str) -> int:
  return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(impact, 9)


def audit_resources(*, include_runtime: bool = True) -> Dict[str, Any]:
  """Full gap audit with challenge questions and prioritized action items."""
  items: List[dict] = []
  for raw in WATCHLIST:
    entry = dict(raw)
    entry["status"] = _resolve_status(raw)
    items.append(entry)

  gaps = [
    i for i in items
    if i["status"] in ("missing", "partial") and i.get("impact") in ("critical", "high", "medium")
  ]
  gaps.sort(key=lambda x: (_impact_rank(x.get("impact", "low")), x.get("category", "")))

  challenges = [i["challenge"] for i in gaps[:12]]
  challenges.extend([
    "Are all CANDIDATE_SOURCES in impact_discovery producing measurable lift with current sample size?",
    "Does executive_intel fuse every free data path or only fear/greed + WS?",
    "Is tv_oss_discovery promoting candidates with positive lift into EW_TV_LAYER_WEIGHTS?",
    "Should we add a nightly GitHub search for new TradingView OSS indicator ports?",
  ])

  tv_counts = _tv_catalog_counts()
  impact_factors = 0
  try:
    from engine.impact_discovery import CANDIDATE_SOURCES

    impact_factors = len(CANDIDATE_SOURCES)
  except ImportError:
    pass

  runtime: Dict[str, Any] = {}
  if include_runtime:
    runtime = {
      "gh_cli": _cli_available("gh"),
      "github_token": bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")),
      "cursor_api": bool(os.environ.get("CURSOR_API_KEY")),
      "kraken_keys": bool(os.environ.get("KRAKEN_API_KEY")),
      "tiktoken": _importable("tiktoken"),
      "websockets": _importable("websockets"),
      "ccxt": _importable("ccxt"),
    }

  by_category: Dict[str, Dict[str, int]] = {}
  for i in items:
    cat = i.get("category", "other")
    by_category.setdefault(cat, {"integrated": 0, "partial": 0, "missing": 0, "candidate": 0})
    by_category[cat][i["status"]] = by_category[cat].get(i["status"], 0) + 1

  return {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "enabled": gap_audit_enabled(),
    "summary": {
      "total_watchlist": len(items),
      "gaps": len(gaps),
      "critical_gaps": sum(1 for g in gaps if g.get("impact") == "critical"),
      "high_gaps": sum(1 for g in gaps if g.get("impact") == "high"),
      "tv_catalog": tv_counts,
      "impact_factors": impact_factors,
      "by_category": by_category,
    },
    "top_gaps": gaps[:15],
    "challenge_questions": challenges[:20],
    "runtime": runtime,
    "items": items,
  }


def save_gap_audit(report: dict) -> Path:
  AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
  AUDIT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
  return AUDIT_PATH


def load_gap_audit() -> dict:
  if not AUDIT_PATH.exists():
    return {}
  try:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}


def run_resource_gap_audit(*, persist: bool = True, persist_okf: bool = True) -> Dict[str, Any]:
  if not gap_audit_enabled():
    return {"skipped": True, "reason": "EW_GAP_AUDIT disabled"}

  report = audit_resources()
  if persist:
    save_gap_audit(report)
  if persist_okf:
    _persist_gap_lessons(report)
  return report


def _persist_gap_lessons(report: dict) -> Dict[str, Any]:
  try:
    from engine.brain_self_improve import persist_lesson, self_improve_enabled

    if not self_improve_enabled():
      return {"persisted": False}
    paths = []
    summary = report.get("summary") or {}
    gaps = summary.get("gaps", 0)
    crit = summary.get("critical_gaps", 0)
    r = persist_lesson(
      "GLOBAL",
      f"gap_audit: {gaps} gaps ({crit} critical) — review resource_gap_audit.json",
      source="gap_audit",
    )
    if r.get("persisted"):
      paths.append(r.get("path"))
    for gap in (report.get("top_gaps") or [])[:3]:
      msg = f"GAP [{gap.get('impact')}] {gap.get('id')}: {gap.get('challenge', '')[:120]}"
      r = persist_lesson("GLOBAL", msg, source="gap_audit")
      if r.get("persisted"):
        paths.append(r.get("path"))
    return {"persisted": bool(paths), "paths": paths}
  except Exception as exc:
    return {"persisted": False, "error": str(exc)}


def gap_audit_summary() -> Dict[str, Any]:
  """Compact summary for improvement cycle / autonomous tick."""
  report = load_gap_audit() or audit_resources(include_runtime=False)
  s = report.get("summary") or {}
  return {
    "gaps": s.get("gaps", 0),
    "critical": s.get("critical_gaps", 0),
    "top_gap_ids": [g.get("id") for g in (report.get("top_gaps") or [])[:5]],
    "challenges": (report.get("challenge_questions") or [])[:3],
  }
