"""Export executable EW rows to Freqtrade-compatible JSON for dry-run validation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_OUT = Path(os.environ.get("EW_FREQTRADE_EXPORT", "output/freqtrade/ew_signals.json"))


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def _normalize_pair(symbol: str) -> str:
  """BTC/USDT -> BTC/USDT (Freqtrade format)."""
  return symbol.replace("-", "/")


def row_to_freqtrade_signal(row: dict) -> Optional[Dict[str, Any]]:
  """Map limit-order export row to a Freqtrade custom signal payload."""
  sym = row.get("symbol")
  if not sym:
    return None
  direction = str(row.get("direction", "")).upper()
  side = "long" if direction in ("LONG", "BULL") else "short" if direction in ("SHORT", "BEAR") else None
  if not side:
    return None
  try:
    entry = float(row.get("wae") or row.get("entry") or 0)
    stop = float(row.get("stop_loss") or 0)
    tp1 = float(row.get("tp1") or 0)
  except (TypeError, ValueError):
    return None
  if entry <= 0 or stop <= 0:
    return None

  return {
    "pair": _normalize_pair(str(sym)),
    "timeframe": str(row.get("timeframe") or "1h"),
    "side": side,
    "entry": entry,
    "stoploss": stop,
    "take_profit": tp1,
    "stake_pct": float(row.get("gtc_size_cap_pct") or 100) / 100.0,
    "setup_id": f"{sym}|{row.get('timeframe')}|{direction}",
    "exported_at": _utcnow(),
    "metadata": {
      "gtc_tier": row.get("gtc_tier"),
      "honest_execution_tier": row.get("honest_execution_tier"),
      "executive_verdict": row.get("executive_verdict"),
    },
  }


def export_freqtrade_signals(
  rows: Optional[List[dict]] = None,
  *,
  csv_path: str = "",
  output_path: Optional[Path] = None,
  max_rows: int = 0,
) -> Dict[str, Any]:
  """
  Export gated executable rows for Freqtrade dry-run ingestion.
  Writes JSON + companion strategy stub README.
  """
  if rows is None:
    from engine.paper_simulator import filter_executable_rows, load_export_csv, rank_rows
    from engine.execution_gates import gate_row

    raw = load_export_csv(csv_path)
    candidates = filter_executable_rows(raw)
    ranked = rank_rows(candidates)
    rows = []
    for row in ranked:
      ok, _reasons = gate_row(row)
      if ok:
        rows.append(row)

  if max_rows and len(rows) > max_rows:
    rows = rows[:max_rows]

  signals = [s for r in rows if (s := row_to_freqtrade_signal(r))]
  out = output_path or DEFAULT_OUT
  out.parent.mkdir(parents=True, exist_ok=True)

  payload = {
    "exported_at": _utcnow(),
    "source": "ew_tool_limit_orders",
    "signal_count": len(signals),
    "signals": signals,
    "freqtrade_notes": {
      "dry_run": "Set dry_run: true in config.json",
      "ingest": "Load signals in custom strategy via ew_signals.json path",
      "docs": "https://www.freqtrade.io/en/stable/",
    },
  }
  out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

  readme = out.parent / "README_FREQTRADE.md"
  readme.write_text(
    "\n".join([
      "# Freqtrade EW Signal Export",
      "",
      f"Generated: `{payload['exported_at']}`",
      f"Signals: **{len(signals)}**",
      "",
      "## Dry-run validation (independent paper proof)",
      "",
      "1. Install Freqtrade: https://www.freqtrade.io/en/stable/installation/",
      "2. Copy `ew_signals.json` into your Freqtrade `user_data/` folder",
      "3. Implement a custom strategy that reads signals on each candle",
      "4. Run: `freqtrade trade --config config.json --strategy EWSignalStrategy --dry-run`",
      "",
      f"> Export path: `{out}`",
      "",
    ]) + "\n",
    encoding="utf-8",
  )

  return {
    "ok": True,
    "signal_count": len(signals),
    "output_path": str(out),
    "readme_path": str(readme),
  }
