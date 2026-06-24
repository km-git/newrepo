"""Live SMC monitor — re-evaluate sweep+OB+FVG between batch runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.institutional_edge import build_institutional_matrix
from core.msb_zscore import validate_msb_zscore
from engine.calibrated_execution import resolve_live_status
from engine.indicator_calibration import apply_extra_calibration_tokens, load_calibration
from fetchers.exchange_client import get_crypto_exchange


def evaluate_smc_triggers(
  item: dict,
  data: Dict[str, Any],
  exchange=None,
  executive_verdict: str = "STAGED_GO",
) -> dict:
  """
  Re-scan SMC confluence on fresh bars.
  Upgrades monitor→executable when entry_signal or entry_probe fires.
  """
  symbol = item["symbol"]
  direction = item.get("direction", "LONG")
  check_tf = item.get("check") or item.get("timeframe") or "15m"
  df = data.get(check_tf)
  if df is None or len(df) < 40:
    return {
      "scanned_at": datetime.now(timezone.utc).isoformat(),
      "error": f"missing {check_tf} data",
      "triggers_hit": [],
      "new_status": item.get("status", "monitor"),
      "price": None,
    }

  price = float(df["Close"].iloc[-1])
  inst = build_institutional_matrix(
    data, direction, tfs=["15m", "1h", "4h"], exchange=exchange, symbol=symbol,
  )
  tf_analysis = inst.get("by_tf", {}).get(check_tf) or {}
  if tf_analysis.get("status") != "ok":
    entry_tf = inst.get("best_entry_tf") or check_tf
    tf_analysis = inst.get("by_tf", {}).get(entry_tf, {})

  msb = validate_msb_zscore(df, direction)

  setup_stub = {
    "style": "smc",
    "direction": direction,
    "timeframe": check_tf,
    "entry_signal": inst.get("entry_signal") or tf_analysis.get("entry_signal"),
    "entry_probe": inst.get("entry_probe") or tf_analysis.get("entry_probe"),
    "entry_grade": inst.get("entry_grade") or tf_analysis.get("entry_grade", "D"),
    "confluence_count": inst.get("confluence_count") or tf_analysis.get("partial_confluence", 0),
    "structure_event": tf_analysis.get("structure_event"),
    "readiness_score": tf_analysis.get("score", 0),
    "indicator_signals": tf_analysis.get("tags", [])[:8],
    "indicators": {"score": tf_analysis.get("score", 0), "threshold": 45, "aligned": tf_analysis.get("score", 0) >= 45},
    "entry": {"anchor": price, "zone": item.get("entry_zone") or [price, price]},
    "stop_loss": {"price": item.get("stop"), "distance_pct": None},
    "targets": [{"price": item.get("tp1"), "rr": 2.0}] if item.get("tp1") else [],
    "oos_win_rate": item.get("oos_win_rate"),
    "oos_trades": item.get("oos_trades", 0),
    "vp_filter_ok": tf_analysis.get("vp_filter_ok", True),
    "entry_confirm_ok": inst.get("entry_confirm_ok") or tf_analysis.get("entry_confirm_ok", False),
    "structure_blocked": inst.get("structure_blocked") or tf_analysis.get("structure_blocked", False),
  }

  cal = load_calibration()
  setup_stub["indicators"] = apply_extra_calibration_tokens(
    setup_stub["indicators"], tf_analysis.get("tags", []),
  )
  from engine.execution_queue import load_audit_status
  setup_stub = resolve_live_status(
    setup_stub, style="smc", executive_verdict=executive_verdict, msb=msb,
    audit_status=load_audit_status(),
  )

  triggers_hit: List[str] = []
  if setup_stub.get("entry_signal"):
    triggers_hit.append("SMC entry_signal: sweep+OB+FVG")
  if setup_stub.get("entry_probe"):
    triggers_hit.append("SMC entry_probe: 2/3 confluence")
  if tf_analysis.get("recent_sweep"):
    triggers_hit.append("liquidity sweep")
  if tf_analysis.get("active_ob"):
    triggers_hit.append("in OB zone")
  if tf_analysis.get("active_fvg"):
    triggers_hit.append("in FVG zone")
  if msb.get("pass"):
    triggers_hit.append("MSB z-score pass (blocked)")
  elif msb.get("status") == "ok":
    triggers_hit.append("MSB z-score weak")

  prior = item.get("status", "monitor")
  new_status = setup_stub.get("status", prior)
  new_tier = setup_stub.get("execution_tier", item.get("execution_tier", "none"))

  upgrade_note = None
  if prior == "monitor" and new_status == "executable":
    upgrade_note = "SMC UPGRADED monitor→executable: " + "; ".join(triggers_hit[:4])
  elif prior == "executable" and new_status == "monitor":
    upgrade_note = "SMC DOWNGRADED: " + setup_stub.get("honest_reason", "")[:120]

  return {
    "scanned_at": datetime.now(timezone.utc).isoformat(),
    "symbol": symbol,
    "style": "smc",
    "check_tf": check_tf,
    "price": round(price, 6),
    "triggers_hit": triggers_hit,
    "prior_status": prior,
    "new_status": new_status,
    "execution_tier": new_tier,
    "entry_signal": setup_stub.get("entry_signal"),
    "entry_probe": setup_stub.get("entry_probe"),
    "entry_grade": setup_stub.get("entry_grade"),
    "confluence_count": setup_stub.get("confluence_count"),
    "institutional_score": tf_analysis.get("score"),
    "msb_pass": msb.get("pass"),
    "msb_z": msb.get("z"),
    "vp_filter_ok": tf_analysis.get("vp_filter_ok"),
    "entry_confirm_ok": setup_stub.get("entry_confirm_ok"),
    "structure_blocked": setup_stub.get("structure_blocked"),
    "oos_gate": setup_stub.get("oos_gate"),
    "upgrade_note": upgrade_note,
    "setup_live": setup_stub,
  }


def scan_smc_item(item: dict, is_crypto: bool = True) -> dict:
  """Fetch and evaluate one SMC queue item."""
  from fetchers import fetch
  symbol = item["symbol"]
  check_tf = item.get("check") or item.get("timeframe") or "15m"
  tfs = list(dict.fromkeys(["15m", "1h", "4h", "1d", check_tf]))
  data = fetch(symbol, tfs, is_crypto)
  exchange = get_crypto_exchange() if is_crypto else None
  scan = evaluate_smc_triggers(item, data, exchange=exchange)
  return {**item, **scan}
