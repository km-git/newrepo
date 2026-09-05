"""Monetization strategy services for trading intelligence outputs.

The report is intentionally deterministic: it packages existing EW outputs
into licensing, access-control, and royalty-reporting service motions without
placing trades, fetching markets, or consulting LLMs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

MONETIZATION_PATH = Path(os.environ.get("EW_MONETIZATION_PATH", "output/system/monetization_strategy.json"))
DEFAULT_BEST_TRADES_PATH = Path("output/v6_scanner/best_trades_latest.json")


def _load_json(path: str | Path) -> Dict[str, Any]:
  p = Path(path)
  if not p.exists():
    return {}
  try:
    return json.loads(p.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}


def _n(value: Any, default: int = 0) -> int:
  try:
    return int(value or default)
  except (TypeError, ValueError):
    return default


def _f(value: Any, default: float = 0.0) -> float:
  try:
    return float(value or default)
  except (TypeError, ValueError):
    return default


def _source_metrics(best_trades: Dict[str, Any]) -> Dict[str, Any]:
  top = list(best_trades.get("top_10") or [])
  executable = _n(best_trades.get("executable_scanned"))
  top_n = _n(best_trades.get("top_n"), len(top))
  scores = [_f(r.get("score")) for r in top if r.get("score") is not None]
  avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
  symbols = sorted({str(r.get("symbol")) for r in top if r.get("symbol")})
  timeframes = sorted({str(r.get("timeframe")) for r in top if r.get("timeframe")})
  return {
    "source_available": bool(best_trades),
    "executable_scanned": executable,
    "top_n": top_n,
    "top_10_avg_score": avg_score,
    "sample_symbols": symbols[:10],
    "sample_timeframes": timeframes,
  }


def _commercial_stage(metrics: Dict[str, Any]) -> str:
  if metrics["executable_scanned"] >= 100 and metrics["top_n"] >= 25:
    return "scale"
  if metrics["executable_scanned"] >= 20 and metrics["top_n"] >= 10:
    return "pilot"
  if metrics["source_available"] and metrics["top_n"] > 0:
    return "private_beta"
  return "design"


def _service_catalog(stage: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
  common_controls = ["api_key", "tenant_entitlements", "symbol_timeframe_scopes", "audit_log"]
  services = [
    {
      "id": "signal_feed",
      "name": "Licensed EW signal feed",
      "buyer": "quant desks, trading communities, broker platforms",
      "offer": "ranked executable setups with WAE, readiness, RR, DCA profile, stops, and targets",
      "license_tag": "signals.internal_use",
      "access_controls": common_controls,
      "royalty_basis": "monthly subscription plus optional usage fee per delivered setup",
      "minimum_stage": "private_beta",
      "ready": stage in ("private_beta", "pilot", "scale"),
    },
    {
      "id": "research_briefings",
      "name": "Premium market research briefings",
      "buyer": "discretionary traders and advisory teams",
      "offer": "human-readable strategy packs from top setups, risk gates, and market-intel overlays",
      "license_tag": "research.no_redistribution",
      "access_controls": ["account_login", "watermarked_exports", "recipient_audit_log"],
      "royalty_basis": "seat-based subscription",
      "minimum_stage": "design",
      "ready": True,
    },
    {
      "id": "white_label_api",
      "name": "White-label API / data product",
      "buyer": "fintech apps and portfolio dashboards",
      "offer": "machine-readable setup rankings, abstentions, and evidence fields for embedded UX",
      "license_tag": "api.redistribution_limited",
      "access_controls": common_controls + ["rate_limits", "signed_payloads"],
      "royalty_basis": "platform fee plus metered API calls",
      "minimum_stage": "pilot",
      "ready": stage in ("pilot", "scale"),
    },
    {
      "id": "paper_execution_service",
      "name": "Paper execution and forward-proof service",
      "buyer": "strategy evaluators and prop-style operators",
      "offer": "LLM-free paper ledger, 30-day forward proof, and effectiveness gates",
      "license_tag": "execution.paper_only",
      "access_controls": ["separate_paper_tenants", "read_only_exports", "ledger_audit_log"],
      "royalty_basis": "managed-service retainer",
      "minimum_stage": "pilot",
      "ready": stage in ("pilot", "scale"),
    },
    {
      "id": "derived_dataset",
      "name": "Derived setup dataset",
      "buyer": "model-training and analytics teams",
      "offer": "historical setup labels, outcomes, features, abstentions, and policy-filter decisions",
      "license_tag": "dataset.training_restricted",
      "access_controls": ["bucket_policy", "kms_key_per_customer", "manifest_hashes"],
      "royalty_basis": "dataset license plus renewal for refreshed snapshots",
      "minimum_stage": "scale",
      "ready": stage == "scale",
    },
  ]
  for svc in services:
    svc["evidence"] = {
      "commercial_stage": stage,
      "executable_scanned": metrics["executable_scanned"],
      "top_n": metrics["top_n"],
    }
  return services


def _blockers(stage: str, metrics: Dict[str, Any]) -> List[str]:
  blockers: List[str] = []
  if not metrics["source_available"]:
    blockers.append("No best-trades artifact found; run a scanner/export before selling signal feeds.")
  if metrics["executable_scanned"] < 20:
    blockers.append("Executable sample is too small for API or paper-execution pilots.")
  if stage != "scale":
    blockers.append("Derived datasets need larger resolved history before customer training use.")
  return blockers


def build_monetization_strategy(
  *,
  best_trades_path: str | Path = DEFAULT_BEST_TRADES_PATH,
  include_runtime: bool = True,
) -> Dict[str, Any]:
  """Build a strategy report for monetizing existing trading-intelligence outputs."""
  best_trades = _load_json(best_trades_path)
  metrics = _source_metrics(best_trades)
  stage = _commercial_stage(metrics)
  services = _service_catalog(stage, metrics)
  ready_services = [s["id"] for s in services if s.get("ready")]

  report: Dict[str, Any] = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "module": "monetize",
    "commercial_stage": stage,
    "source": {
      "best_trades_path": str(best_trades_path),
      "best_trades_available": bool(best_trades),
      "best_trades_timestamp_utc": best_trades.get("timestamp_utc"),
    },
    "metrics": metrics,
    "summary": {
      "ready_services": ready_services,
      "ready_count": len(ready_services),
      "service_count": len(services),
      "primary_motion": ready_services[0] if ready_services else "research_briefings",
    },
    "license_tags": sorted({s["license_tag"] for s in services}),
    "access_control_baseline": [
      "tenant_entitlements",
      "symbol_timeframe_scopes",
      "rate_limits_for_api_products",
      "append_only_delivery_audit",
      "watermarked_human_exports",
    ],
    "royalty_reporting": {
      "events": ["setup_delivered", "briefing_exported", "api_call", "dataset_snapshot_delivered"],
      "dimensions": ["tenant", "service_id", "symbol", "timeframe", "license_tag"],
      "minimum_fields": ["event_id", "timestamp_utc", "tenant_id", "service_id", "quantity", "royalty_basis"],
    },
    "services": services,
    "blockers": _blockers(stage, metrics),
    "next_actions": [
      "Keep all live trading disabled for commercial services unless explicit live-execution gates pass.",
      "Attach license tags and tenant entitlements to every exported setup before redistribution.",
      "Report royalties from immutable delivery events, not from mutable customer invoices.",
    ],
  }
  if include_runtime:
    report["runtime"] = {
      "output_path": str(MONETIZATION_PATH),
      "env_path_override": bool(os.environ.get("EW_MONETIZATION_PATH")),
    }
  return report


def save_monetization_strategy(report: Optional[dict] = None) -> str:
  report = report or build_monetization_strategy()
  MONETIZATION_PATH.parent.mkdir(parents=True, exist_ok=True)
  MONETIZATION_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
  return str(MONETIZATION_PATH)
