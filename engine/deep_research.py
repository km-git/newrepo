"""Deep research — web intel, websockets, social scraping, AI synthesis."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

RESEARCH_PATH = Path(os.environ.get("EW_DEEP_RESEARCH_STATE", "output/system/deep_research.json"))


def deep_research_enabled() -> bool:
  return os.environ.get("EW_DEEP_RESEARCH", "1").lower() not in ("0", "false", "no")


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def gather_market_intel(symbols: Optional[List[str]] = None) -> Dict[str, Any]:
  """Pull Fear&Greed, dominance, funding, social signals for top symbols."""
  symbols = symbols or ["BTC/USDT", "ETH/USDT"]
  out: Dict[str, Any] = {"timestamp_utc": _utcnow(), "symbols": {}}

  if os.environ.get("EW_WEB_INTEL", "1").lower() not in ("0", "false", "no"):
    try:
      from gateway.web_intel import build_web_intel, fear_greed_index, coingecko_global

      out["macro"] = {
        "fear_greed": fear_greed_index(),
        "global": coingecko_global(),
      }
      for sym in symbols[:5]:
        try:
          out["symbols"][sym] = build_web_intel(sym)
        except Exception as exc:
          out["symbols"][sym] = {"error": str(exc)}
    except Exception as exc:
      out["macro_error"] = str(exc)

  if os.environ.get("EW_SOCIAL_INTEL", "1").lower() not in ("0", "false", "no"):
    try:
      from gateway.social_intel import build_social_intel

      out["social"] = build_social_intel(symbols[0])
    except Exception as exc:
      out["social"] = {"error": str(exc)}

  return out


def gather_live_ws(symbols: Optional[List[str]] = None) -> Dict[str, Any]:
  """WebSocket ticker snapshots via ws_hub (Kraken/OKX)."""
  symbols = symbols or ["BTC/USDT"]
  if os.environ.get("EW_WS_ENABLED", "0").lower() in ("0", "false", "no"):
    return {"skipped": True, "reason": "EW_WS_ENABLED off"}

  try:
    from gateway.data_hub import live_market_state

    states = {}
    for sym in symbols[:3]:
      states[sym] = live_market_state(sym, start_ws=True)
    return {"timestamp_utc": _utcnow(), "states": states}
  except Exception as exc:
    return {"error": str(exc)}


def run_deep_research(
  *,
  symbols: Optional[List[str]] = None,
  use_ai: bool = True,
) -> Dict[str, Any]:
  """
  Full deep research pass:
  1. Web scraping + API intel (Fear&Greed, CoinGecko, funding)
  2. Social strategy validation
  3. WebSocket live state
  4. Impact discovery hidden factors
  5. AI multi-model synthesis (cheap first, escalate if macro risk-off)
  """
  if not deep_research_enabled():
    return {"skipped": True, "reason": "EW_DEEP_RESEARCH disabled"}

  intel = gather_market_intel(symbols)
  ws = gather_live_ws(symbols)

  impact = {}
  if os.environ.get("EW_IMPACT_DISCOVERY", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.impact_discovery import run_impact_discovery

      impact = run_impact_discovery()
    except Exception as exc:
      impact = {"error": str(exc)}

  social = {}
  if os.environ.get("EW_SOCIAL_VALIDATION", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.social_strategy_validation import run_social_strategy_validation

      social = run_social_strategy_validation(use_llm=use_ai and os.environ.get("EW_ROUTINE_LLM", "0").lower() in ("1", "true"))
    except Exception as exc:
      social = {"error": str(exc)}

  tv_oss = {}
  if os.environ.get("EW_TV_OSS_CONSENSUS", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.tv_oss_consensus import run_tv_oss_consensus

      tv_llm = use_ai and os.environ.get("EW_ROUTINE_LLM", "0").lower() in ("1", "true")
      tv_oss = run_tv_oss_consensus(use_llm=tv_llm)
    except Exception as exc:
      tv_oss = {"error": str(exc)}

  ai_synthesis: Dict[str, Any] = {}
  if use_ai and os.environ.get("EW_AI_IMPROVEMENT", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.ai_improvement import run_multi_model_improvement_review

      macro = (intel.get("macro") or {}).get("fear_greed") or {}
      fg_val = macro.get("value", 50)
      ai_synthesis = run_multi_model_improvement_review(
        metrics={"overall": {"win_rate": None}, "macro_fear_greed": fg_val},
        use_cache=True,
      )
    except Exception as exc:
      ai_synthesis = {"error": str(exc)}

  result = {
    "timestamp_utc": _utcnow(),
    "intel": intel,
    "websocket": ws,
    "impact": {
      "recommendations": impact.get("recommendations", []) if isinstance(impact, dict) else [],
      "top_boosts": (impact.get("discovery") or {}).get("top_boosts", [])[:5] if isinstance(impact, dict) else [],
    },
    "social": social,
    "tv_oss": tv_oss,
    "ai_synthesis": {
      "stance": ai_synthesis.get("consensus_stance"),
      "summary": (ai_synthesis.get("blended_summary") or "")[:500],
      "models": len(ai_synthesis.get("models_consulted") or []),
      "escalated": ai_synthesis.get("escalated_to_premium"),
    } if ai_synthesis and not ai_synthesis.get("skipped") else ai_synthesis,
  }

  _persist(result)
  _persist_lessons(result)
  return result


def _persist(result: dict) -> None:
  RESEARCH_PATH.parent.mkdir(parents=True, exist_ok=True)
  RESEARCH_PATH.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


def _persist_lessons(result: dict) -> None:
  try:
    from engine.brain_self_improve import persist_lesson, self_improve_enabled

    if not self_improve_enabled():
      return
    fg = ((result.get("intel") or {}).get("macro") or {}).get("fear_greed") or {}
    ai = result.get("ai_synthesis") or {}
    lesson = (
      f"deep_research fg={fg.get('value')} bias={fg.get('bias')} "
      f"ai={ai.get('stance')} models={ai.get('models', 0)}"
    )
    persist_lesson("GLOBAL", lesson[:200], source="deep_research")
  except Exception:
    pass


def load_deep_research() -> dict:
  if not RESEARCH_PATH.exists():
    return {}
  try:
    return json.loads(RESEARCH_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}
