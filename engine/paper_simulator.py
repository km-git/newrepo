"""
OHLC-based paper execution — limit DCA fills, fees, portfolio cap, realized P&L.

Unlike paper_ledger (instant fill) or outcome_tracker (WAE entry proxy), this module:
- Fills GTC limits when bar high/low touches leg price
- Applies taker fee on each leg entry and exit
- Caps concurrent setups (default 3)
- Produces dollar P&L and reports for the closed loop
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.execution_gates import gate_row
from engine.execution_router import filter_executable_rows
from engine.outcome_tracker import _MAX_FORWARD_BARS

STATE_PATH = Path(os.environ.get("EW_PAPER_SIM_STATE", "output/execution/paper_sim_state.json"))
PNL_MD_PATH = Path(os.environ.get("EW_PAPER_PNL_MD", "reports/PAPER_PNL.md"))
PNL_JSON_PATH = Path(os.environ.get("EW_PAPER_PNL_JSON", "output/execution/paper_pnl.json"))


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def fee_rate() -> float:
  return float(os.environ.get("EW_PAPER_FEE_RATE", "0.0026"))


def max_positions() -> int:
  return int(os.environ.get("EW_PAPER_MAX_POSITIONS", "3"))


def require_kill_zone() -> bool:
  return os.environ.get("EW_PAPER_REQUIRE_KILL_ZONE", "1").lower() not in ("0", "false", "no")


def disabled_timeframes() -> set:
  raw = os.environ.get("EW_PAPER_DISABLE_TFS", "1w")
  return {t.strip() for t in raw.split(",") if t.strip()}


def normalize_export_row(row: dict) -> dict:
  """Fill defaults for slim executable-only CSV exports."""
  r = dict(row)
  if not r.get("gtc_tier"):
    r["gtc_tier"] = "executable"
  if not r.get("row_type"):
    r["row_type"] = "primary"
  if not r.get("in_kill_zone"):
    r["in_kill_zone"] = os.environ.get("EW_PAPER_ASSUME_IN_ZONE", "Y")
  if not r.get("macro_mode"):
    r["macro_mode"] = "NEUTRAL"
  if not r.get("executive_verdict"):
    r["executive_verdict"] = "CONDITIONAL_GO"
  return r


def load_export_csv(path: str = "") -> List[dict]:
  p = Path(path or os.environ.get("EW_LIMIT_ORDERS_CSV", "output/latest_limit_orders_all_tf.csv"))
  if not p.exists():
    slim = Path("reports/latest_executable_pair_tf.csv")
    if slim.exists():
      p = slim
    else:
      return []
  with p.open(newline="", encoding="utf-8") as f:
    return [normalize_export_row(r) for r in csv.DictReader(f)]


def _parse_json_field(val: Any) -> Any:
  if isinstance(val, str) and val.startswith(("[", "{")):
    try:
      return json.loads(val)
    except json.JSONDecodeError:
      return val
  return val


def extract_legs(row: dict) -> List[dict]:
  """DCA legs with USD notional from export row."""
  dca = _parse_json_field(row.get("dca_legs")) or []
  cap = float(row.get("gtc_size_cap_pct") or 100) / 100.0
  if row.get("honest_execution_tier") == "probe":
    cap = min(cap, 0.5)
  legs: List[dict] = []
  if isinstance(dca, list) and dca:
    for leg in dca:
      n = int(leg.get("leg") or len(legs) + 1)
      price = float(leg.get("price") or 0)
      if price <= 0:
        continue
      usd_key = f"leg{n}_usd"
      usd = float(row.get(usd_key) or 0)
      if usd <= 0:
        pos = float(row.get("position_notional_usd") or 0)
        pct = float(leg.get("size_pct") or 0) / 100.0
        usd = pos * pct * cap
      if usd > 0:
        legs.append({"leg": n, "price": price, "usd": round(usd, 2)})
    return legs

  # Slim CSV fallback: dca_* columns
  for n, col in enumerate(
    ("dca_10pct_price", "dca_20pct_price", "dca_30pct_price", "dca_40pct_price"), start=1
  ):
    price = float(row.get(col) or 0)
    usd = float(row.get(f"leg{n}_usd") or 0)
    if price > 0 and usd > 0:
      legs.append({"leg": n, "price": price, "usd": round(usd, 2)})

  wae = float(row.get("wae") or 0)
  notional = float(row.get("position_notional_usd") or 0)
  if not legs and wae > 0 and notional > 0:
    legs.append({"leg": 1, "price": wae, "usd": round(notional * cap, 2)})
  return legs


def gate_paper_row(row: dict, *, open_positions: int = 0) -> Tuple[bool, List[str]]:
  """Honest export gates + paper portfolio rules."""
  allowed, reasons = gate_row(row, intel={})
  if not allowed:
    return False, reasons

  if require_kill_zone() and row.get("in_kill_zone") != "Y":
    return False, ["not_in_kill_zone"]

  tf = row.get("timeframe", "")
  if tf in disabled_timeframes():
    return False, [f"tf_disabled={tf}"]

  if open_positions >= max_positions():
    return False, [f"max_positions={max_positions()}"]

  legs = extract_legs(row)
  if not legs:
    return False, ["no_dca_legs"]

  try:
    stop = float(row.get("stop_loss") or 0)
    tp1 = float(row.get("tp1") or 0)
  except (TypeError, ValueError):
    return False, ["invalid_sl_tp"]
  if stop <= 0 or tp1 <= 0:
    return False, ["invalid_sl_tp"]

  return True, []


def rank_rows(rows: List[dict]) -> List[dict]:
  """FULL before PROBE; in-zone first; shorter TF slightly preferred."""

  def key(r: dict) -> tuple:
    tier = 0 if r.get("honest_execution_tier") == "full" else 1
    zone = 0 if r.get("in_kill_zone") == "Y" else 1
    tf = r.get("timeframe", "1w")
    tf_rank = {"15m": 0, "1h": 1, "4h": 2, "1d": 3, "1w": 4}.get(tf, 5)
    hist = 0 if r.get("hist_action") == "downgrade" else 1
    return (tier, zone, hist, tf_rank)

  return sorted(rows, key=key)


def limit_fills_on_bar(direction: str, limit_price: float, high: float, low: float) -> bool:
  long = direction.upper() in ("LONG", "BULL")
  if long:
    return low <= limit_price
  return high >= limit_price


def _is_long(direction: str) -> bool:
  return direction.upper() in ("LONG", "BULL")


def _stop_hit(direction: str, stop: float, high: float, low: float) -> bool:
  if _is_long(direction):
    return low <= stop
  return high >= stop


def _tp_hit(direction: str, tp: float, high: float, low: float) -> bool:
  if _is_long(direction):
    return high >= tp
  return low <= tp


def simulate_trade_on_bars(
  row: dict,
  highs: List[float],
  lows: List[float],
  *,
  fee: Optional[float] = None,
) -> dict:
  """
  Walk OHLC bars: fill DCA limits, then manage SL / TP1–TP3 exits.
  Conservative: SL checked before TPs on each bar.
  """
  fee = fee if fee is not None else fee_rate()
  symbol = row.get("symbol", "")
  tf = row.get("timeframe", "")
  direction = row.get("direction", "LONG")
  long = _is_long(direction)
  setup_id = f"{symbol}|{tf}|{direction}"

  legs = extract_legs(row)
  stop = float(row.get("stop_loss") or 0)
  tps = [
    (float(row.get("tp1") or 0), float(row.get("tp1_exit_pct") or 33)),
    (float(row.get("tp2") or 0), float(row.get("tp2_exit_pct") or 33)),
    (float(row.get("tp3") or 0), float(row.get("tp3_exit_pct") or 34)),
  ]

  pending = [dict(l, filled=False) for l in legs]
  fills: List[dict] = []
  exits: List[dict] = []
  total_qty = 0.0
  cash_spent = 0.0  # long: cost incl fees; short: negative = credit received
  fees_paid = 0.0
  status = "no_fill"
  exit_reason = ""

  for bar_i, (h, l) in enumerate(zip(highs, lows)):
    for leg in pending:
      if leg["filled"]:
        continue
      if limit_fills_on_bar(direction, leg["price"], h, l):
        qty = leg["usd"] / leg["price"]
        leg_fee = leg["usd"] * fee
        leg["filled"] = True
        leg["qty"] = qty
        leg["bar"] = bar_i
        total_qty += qty
        if long:
          cash_spent += leg["usd"] + leg_fee
        else:
          cash_spent -= leg["usd"] - leg_fee
        fees_paid += leg_fee
        fills.append({
          "leg": leg["leg"],
          "price": leg["price"],
          "usd": leg["usd"],
          "qty": round(qty, 8),
          "fee_usd": round(leg_fee, 4),
          "bar": bar_i,
        })

    if total_qty <= 0:
      continue

    exited_qty = sum(e["qty"] for e in exits)
    remaining_qty = total_qty - exited_qty
    if remaining_qty <= 1e-15:
      status = "closed_tp"
      exit_reason = "all_tps"
      break

    if _stop_hit(direction, stop, h, l):
      exit_price = stop
      exit_usd = remaining_qty * exit_price
      exit_fee = exit_usd * fee
      if long:
        entry_cost = cash_spent * (remaining_qty / total_qty)
        pnl_leg = exit_usd - exit_fee - entry_cost
      else:
        entry_credit = abs(cash_spent) * (remaining_qty / total_qty)
        pnl_leg = entry_credit - exit_usd - exit_fee
      exits.append({
        "type": "sl",
        "price": exit_price,
        "qty": remaining_qty,
        "usd": round(exit_usd, 2),
        "fee_usd": round(exit_fee, 4),
        "pnl_usd": round(pnl_leg, 2),
        "bar": bar_i,
      })
      fees_paid += exit_fee
      status = "closed_sl"
      exit_reason = "stop_loss"
      break

    for tp_i, (tp_price, exit_pct) in enumerate(tps, start=1):
      if tp_price <= 0 or exit_pct <= 0:
        continue
      exited_qty = sum(e["qty"] for e in exits)
      remaining_qty = total_qty - exited_qty
      if remaining_qty <= 1e-15:
        break
      if _tp_hit(direction, tp_price, h, l):
        tp_qty = min(total_qty * (exit_pct / 100.0), remaining_qty)
        if tp_qty <= 0:
          continue
        exit_usd = tp_qty * tp_price
        exit_fee = exit_usd * fee
        if long:
          entry_cost = cash_spent * (tp_qty / total_qty)
          pnl_leg = exit_usd - exit_fee - entry_cost
        else:
          entry_credit = abs(cash_spent) * (tp_qty / total_qty)
          pnl_leg = entry_credit - exit_usd - exit_fee
        exits.append({
          "type": f"tp{tp_i}",
          "price": tp_price,
          "qty": tp_qty,
          "usd": round(exit_usd, 2),
          "fee_usd": round(exit_fee, 4),
          "pnl_usd": round(pnl_leg, 2),
          "bar": bar_i,
        })
        fees_paid += exit_fee

    exited_qty = sum(e["qty"] for e in exits)
    if total_qty > 0 and exited_qty >= total_qty * 0.99:
      status = "closed_tp"
      exit_reason = "targets"
      break

  filled_any = any(l["filled"] for l in pending)
  if not filled_any:
    status = "no_fill"
  elif status not in ("closed_sl", "closed_tp"):
    status = "open"

  realized_pnl = round(sum(e.get("pnl_usd", 0) for e in exits), 2)
  filled_usd = sum(f["usd"] for f in fills)
  avg_entry = (filled_usd / sum(f["qty"] for f in fills)) if fills else 0.0

  return {
    "setup_id": setup_id,
    "symbol": symbol,
    "timeframe": tf,
    "direction": direction,
    "honest_execution_tier": row.get("honest_execution_tier"),
    "in_kill_zone": row.get("in_kill_zone"),
    "status": status,
    "exit_reason": exit_reason,
    "fills": fills,
    "exits": exits,
    "filled_usd": round(filled_usd, 2),
    "avg_entry": round(avg_entry, 8),
    "fees_usd": round(fees_paid, 2),
    "realized_pnl_usd": realized_pnl,
    "bars_walked": len(highs),
    "legs_filled": len(fills),
    "legs_total": len(legs),
  }


def _tail_bars(df, max_bars: int) -> Tuple[List[float], List[float]]:
  if df is None or len(df) == 0:
    return [], []
  tail = df.tail(max_bars)
  return tail["High"].astype(float).tolist(), tail["Low"].astype(float).tolist()


def run_paper_simulation(
  rows: Optional[List[dict]] = None,
  *,
  csv_path: str = "",
  equity_usd: Optional[float] = None,
  fetch_ohlc: bool = True,
) -> Dict[str, Any]:
  """
  Simulate executable export rows on recent OHLC with portfolio cap.
  Returns summary + per-trade results; persists state and markdown report.
  """
  rows = rows if rows is not None else load_export_csv(csv_path)
  equity = float(equity_usd or os.environ.get("ACCOUNT_EQUITY", "50000"))

  candidates = filter_executable_rows(rows)
  ranked = rank_rows(candidates)

  selected: List[dict] = []
  blocked: List[dict] = []
  open_count = 0

  for row in ranked:
    ok, reasons = gate_paper_row(row, open_positions=open_count)
    if ok:
      selected.append(row)
      open_count += 1
    else:
      blocked.append({
        "symbol": row.get("symbol"),
        "timeframe": row.get("timeframe"),
        "reasons": reasons,
      })

  results: List[dict] = []
  fetch_cache: Dict[str, Any] = {}

  if fetch_ohlc:
    from fetchers import fetch

  for row in selected:
    sym = row["symbol"]
    tf = row["timeframe"]
    max_bars = _MAX_FORWARD_BARS.get(tf, 48)
    highs, lows = [], []

    if fetch_ohlc:
      cache_key = f"{sym}|{tf}"
      if cache_key not in fetch_cache:
        try:
          fetch_cache[cache_key] = fetch(sym, [tf], is_crypto=True).get(tf)
        except Exception as exc:
          fetch_cache[cache_key] = None
          results.append({
            "setup_id": f"{sym}|{tf}|{row.get('direction')}",
            "symbol": sym,
            "timeframe": tf,
            "status": "error",
            "error": str(exc),
          })
          continue
      highs, lows = _tail_bars(fetch_cache[cache_key], max_bars)

    if not highs:
      results.append({
        "setup_id": f"{sym}|{tf}|{row.get('direction')}",
        "symbol": sym,
        "timeframe": tf,
        "status": "error",
        "error": "no_ohlc",
      })
      continue

    trade = simulate_trade_on_bars(row, highs, lows)
    trade["wae"] = row.get("wae")
    trade["risk_budget_usd"] = row.get("risk_budget_usd")
    results.append(trade)

  total_pnl = round(sum(r.get("realized_pnl_usd", 0) for r in results), 2)
  total_fees = round(sum(r.get("fees_usd", 0) for r in results), 2)
  wins = sum(1 for r in results if r.get("realized_pnl_usd", 0) > 0)
  losses = sum(1 for r in results if r.get("realized_pnl_usd", 0) < 0)
  no_fill = sum(1 for r in results if r.get("status") == "no_fill")

  summary = {
    "ok": True,
    "run_at": _utcnow(),
    "starting_equity_usd": equity,
    "ending_equity_usd": round(equity + total_pnl, 2),
    "realized_pnl_usd": total_pnl,
    "fees_usd": total_fees,
    "fee_rate": fee_rate(),
    "max_positions": max_positions(),
    "candidates": len(candidates),
    "simulated": len(results),
    "blocked_count": len(blocked),
    "wins": wins,
    "losses": losses,
    "no_fill": no_fill,
    "trades": results,
    "blocked": blocked,
  }

  _save_state(summary)
  write_paper_pnl_report(summary)
  return summary


def _save_state(summary: dict) -> None:
  STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
  STATE_PATH.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
  PNL_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
  PNL_JSON_PATH.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")


def write_paper_pnl_report(summary: dict, path: Optional[Path] = None) -> str:
  path = path or PNL_MD_PATH
  path.parent.mkdir(parents=True, exist_ok=True)

  lines = [
    "# Paper Execution P&L",
    "",
    f"**Run:** {summary.get('run_at', '')}  ",
    f"**Equity:** ${summary.get('starting_equity_usd', 0):,.2f} → "
    f"${summary.get('ending_equity_usd', 0):,.2f}  ",
    f"**Realized P&L:** ${summary.get('realized_pnl_usd', 0):,.2f}  ",
    f"**Fees:** ${summary.get('fees_usd', 0):,.2f} @ {summary.get('fee_rate', 0)*100:.2f}%  ",
    f"**Max positions:** {summary.get('max_positions', 3)}  ",
    "",
    "## Summary",
    "",
    "| Metric | Value |",
    "|--------|-------|",
    f"| Executable candidates | {summary.get('candidates', 0)} |",
    f"| Simulated (cap) | {summary.get('simulated', 0)} |",
    f"| Blocked | {summary.get('blocked_count', 0)} |",
    f"| Wins | {summary.get('wins', 0)} |",
    f"| Losses | {summary.get('losses', 0)} |",
    f"| No fill | {summary.get('no_fill', 0)} |",
    "",
    "## Simulated Trades",
    "",
    "| Symbol | TF | Tier | Status | Legs | P&L $ | Fees $ | Avg entry |",
    "|--------|-----|------|--------|------|-------|--------|-----------|",
  ]

  for t in summary.get("trades", []):
    if t.get("status") == "error":
      lines.append(
        f"| {t.get('symbol')} | {t.get('timeframe')} | — | error | — | — | — | {t.get('error', '')} |"
      )
      continue
    lines.append(
      f"| {t.get('symbol')} | {t.get('timeframe')} | {t.get('honest_execution_tier', '')} | "
      f"{t.get('status')} | {t.get('legs_filled', 0)}/{t.get('legs_total', 0)} | "
      f"${t.get('realized_pnl_usd', 0):,.2f} | ${t.get('fees_usd', 0):,.2f} | "
      f"{t.get('avg_entry', '')} |"
    )

  blocked = summary.get("blocked") or []
  if blocked:
    lines.extend(["", "## Blocked (portfolio / gates)", ""])
    lines.append("| Symbol | TF | Reasons |")
    lines.append("|--------|-----|---------|")
    for b in blocked[:30]:
      lines.append(
        f"| {b.get('symbol')} | {b.get('timeframe')} | {', '.join(b.get('reasons', []))} |"
      )
    if len(blocked) > 30:
      lines.append(f"| … | … | +{len(blocked) - 30} more |")

  lines.append("")
  lines.append("> OHLC limit fills · fees on entry+exit · SL before TP on same bar")
  lines.append("> Source: `engine/paper_simulator.py`")
  path.write_text("\n".join(lines) + "\n", encoding="utf-8")
  return str(path)
