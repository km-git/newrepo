"""QuantStats tear sheets + cost sensitivity analytics."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import pandas as pd

from engine.profit_lab.setup_returns import equity_curve_from_returns, pct_returns_from_r

REPORT_HTML = Path(os.environ.get("EW_PROFIT_LAB_HTML", "reports/PROFIT_LAB_TEARSHEET.html"))
REPORT_JSON = Path(os.environ.get("EW_PROFIT_LAB_COST_JSON", "output/profit_lab/cost_analytics.json"))


def _html_path() -> Path:
  return Path(os.environ.get("EW_PROFIT_LAB_HTML", str(REPORT_HTML)))


def _cost_json_path() -> Path:
  return Path(os.environ.get("EW_PROFIT_LAB_COST_JSON", str(REPORT_JSON)))


def run_cost_analytics(
  returns_r: Sequence[float],
  *,
  dates: Optional[Sequence] = None,
  equity_start: float = 50_000.0,
  write_html: bool = True,
) -> Dict[str, Any]:
  """Fee-adjusted return analytics with quantstats + cost impact sweep."""
  result: Dict[str, Any] = {"ok": False}
  if len(returns_r) < 2:
    result["reason"] = "insufficient_returns"
    return result

  pct = pct_returns_from_r(returns_r)
  if dates is not None and len(dates) == len(pct):
    idx = pd.DatetimeIndex(pd.to_datetime(list(dates), utc=True))
    pct.index = idx
  else:
    pct.index = pd.date_range(end=pd.Timestamp.utcnow(), periods=len(pct), freq="D")

  curve = equity_curve_from_returns(returns_r, equity_start=equity_start)
  result["equity_start"] = equity_start
  result["equity_end"] = round(curve[-1], 2)
  result["total_return_pct"] = round((curve[-1] / equity_start - 1) * 100, 4)
  result["n_trades"] = len(returns_r)
  result["expectancy_r"] = round(float(sum(returns_r) / len(returns_r)), 6)

  # Cost impact sweep — extra bps drag on top of fee-adjusted returns
  sweep_bps = [0, 5, 10, 15, 20, 30, 50]
  impact_rows = []
  risk_pct = float(os.environ.get("EW_ACCOUNT_RISK_PCT", "0.75")) / 100.0
  for bps in sweep_bps:
    extra_r = -(bps / 10_000.0) / risk_pct if risk_pct > 0 else 0.0
    adj = [r + extra_r for r in returns_r]
    eq = equity_curve_from_returns(adj, equity_start=equity_start)
    impact_rows.append({
      "extra_bps": bps,
      "equity_end": round(eq[-1], 2),
      "expectancy_r": round(float(sum(adj) / len(adj)), 6),
      "profitable": eq[-1] > equity_start,
    })
  result["cost_impact_sweep"] = impact_rows
  breakeven_bps = next((r["extra_bps"] for r in impact_rows if not r["profitable"]), None)
  result["breakeven_extra_bps"] = breakeven_bps

  # jquantstats-style cost analysis when available
  try:
    import polars as pl
    from jquantstats.data import Data

    data = Data.from_returns(pl.DataFrame({
      "date": pct.index,
      "strategy": pct.values,
    }))
    stats = data.stats
    result["jqs_sharpe"] = _safe_call(stats, "sharpe")
    result["jqs_sortino"] = _safe_call(stats, "sortino")
    result["jqs_max_drawdown"] = _safe_call(stats, "max_drawdown")
    result["jqs_calmar"] = _safe_call(stats, "calmar")
    result["jqs_available"] = True
  except Exception as exc:
    result["jqs_available"] = False
    result["jqs_error"] = str(exc)

  # quantstats HTML tear sheet
  if write_html:
    try:
      import quantstats as qs

      qs.extend_pandas()
      _html_path().parent.mkdir(parents=True, exist_ok=True)
      qs.reports.html(
        pct,
        output=str(_html_path()),
        title="EW Profit Lab — Fee-Adjusted Returns",
      )
      result["html_report"] = str(_html_path())
    except Exception as exc:
      result["quantstats_error"] = str(exc)

  result["ok"] = True
  json_path = _cost_json_path()
  json_path.parent.mkdir(parents=True, exist_ok=True)
  json_path.write_text(
    __import__("json").dumps(result, indent=2, default=str),
    encoding="utf-8",
  )
  result["json_path"] = str(json_path)
  return result


def _safe_call(stats, name: str):
  try:
    fn = getattr(stats, name, None)
    if callable(fn):
      v = fn()
      return round(float(v), 6) if v is not None else None
  except Exception:
    return None
  return None
