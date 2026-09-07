"""
Learned paper-execution policy — symbol blocklist and major preference from outcomes.

LLM-free: aggregates realized P&L from paper trade history and blocks repeat losers.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from engine.execution_advanced import CONTINGENT_SYMBOLS

TRADES_PATH = Path(os.environ.get("EW_PAPER_TRADES_LOG", "output/execution/paper_trades.jsonl"))
POLICY_PATH = Path(os.environ.get("EW_PAPER_LEARNED_POLICY", "output/execution/paper_learned_policy.json"))
REPORT_PATH = Path(os.environ.get("EW_PAPER_POLICY_REPORT", "reports/PAPER_POLICY.md"))


def _trades_path() -> Path:
  return Path(os.environ.get("EW_PAPER_TRADES_LOG", str(TRADES_PATH)))


def _policy_path() -> Path:
  return Path(os.environ.get("EW_PAPER_LEARNED_POLICY", str(POLICY_PATH)))


def _report_path() -> Path:
  return Path(os.environ.get("EW_PAPER_POLICY_REPORT", str(REPORT_PATH)))


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def major_symbols() -> frozenset:
  extra = os.environ.get("EW_PAPER_MAJOR_SYMBOLS", "SOL/USDT")
  majors = set(CONTINGENT_SYMBOLS)
  for sym in extra.split(","):
    sym = sym.strip()
    if sym:
      majors.add(sym)
  return frozenset(majors)


def env_blocklist() -> Set[str]:
  raw = os.environ.get("EW_PAPER_SYMBOL_BLOCKLIST", "")
  defaults = os.environ.get("EW_PAPER_JUNK_SYMBOLS", "GRVT/USDT,CHIP/USDT")
  symbols: Set[str] = set()
  for part in (raw, defaults):
    for sym in part.split(","):
      sym = sym.strip()
      if sym:
        symbols.add(sym)
  return symbols


def load_learned_policy() -> dict:
  path = _policy_path()
  if not path.exists():
    return {}
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}


def symbol_blocklist() -> Set[str]:
  """Union of env blocklist and learned blocklist."""
  blocked = env_blocklist()
  policy = load_learned_policy()
  for sym in policy.get("block_symbols") or []:
    blocked.add(sym)
  return blocked


def is_symbol_blocked(symbol: str) -> bool:
  return (symbol or "") in symbol_blocklist()


def record_paper_trades(summary: dict) -> int:
  """Append simulated trades from a paper run to the learning log."""
  trades = summary.get("trades") or []
  if not trades:
    return 0
  path = _trades_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  recorded = 0
  with path.open("a", encoding="utf-8") as f:
    for t in trades:
      if t.get("status") == "error":
        continue
      entry = {
        "recorded_at": summary.get("run_at") or _utcnow(),
        "as_of": summary.get("as_of"),
        "symbol": t.get("symbol"),
        "timeframe": t.get("timeframe"),
        "direction": t.get("direction"),
        "status": t.get("status"),
        "realized_pnl_usd": t.get("realized_pnl_usd"),
        "fees_usd": t.get("fees_usd"),
        "honest_execution_tier": t.get("honest_execution_tier"),
      }
      f.write(json.dumps(entry, default=str) + "\n")
      recorded += 1
  return recorded


def _load_trade_log() -> List[dict]:
  path = _trades_path()
  if not path.exists():
    return []
  rows: List[dict] = []
  for line in path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
      continue
    try:
      rows.append(json.loads(line))
    except json.JSONDecodeError:
      continue
  return rows


def _export_symbols() -> Set[str]:
  """Symbols present in latest limit-order export (ignore test fixtures)."""
  try:
    import csv
    import os
    from pathlib import Path

    path = Path(os.environ.get("EW_LIMIT_ORDERS_CSV", "output/latest_limit_orders_all_tf.csv"))
    if not path.exists():
      return set()
    with path.open(newline="", encoding="utf-8") as f:
      return {r.get("symbol") for r in csv.DictReader(f) if r.get("symbol")}
  except Exception:
    return set()


def learn_symbol_policy(
  *,
  min_trades: Optional[int] = None,
  min_loss_usd: Optional[float] = None,
) -> Dict[str, Any]:
  """
  Block symbols with repeated negative paper P&L.
  Promote majors list is static; blocklist is learned from trade log.
  """
  min_trades = min_trades if min_trades is not None else int(os.environ.get("EW_PAPER_LEARN_MIN_TRADES", "2"))
  min_loss_usd = min_loss_usd if min_loss_usd is not None else float(
    os.environ.get("EW_PAPER_LEARN_MIN_LOSS_USD", "5")
  )

  by_symbol: Dict[str, Dict[str, Any]] = defaultdict(
    lambda: {"trades": 0, "wins": 0, "losses": 0, "pnl_usd": 0.0}
  )
  test_fixtures = {"JUNK/USDT", "GOOD/USDT", "BAD/USDT"}
  export_only = os.environ.get("EW_PAPER_LEARN_EXPORT_ONLY", "0").lower() in ("1", "true", "yes")
  export_syms = _export_symbols() if export_only else set()

  for row in _load_trade_log():
    sym = row.get("symbol") or ""
    if not sym or sym in test_fixtures:
      continue
    if export_syms and sym not in export_syms:
      continue
    pnl = float(row.get("realized_pnl_usd") or 0)
    agg = by_symbol[sym]
    agg["trades"] += 1
    agg["pnl_usd"] = round(agg["pnl_usd"] + pnl, 2)
    if pnl > 0:
      agg["wins"] += 1
    elif pnl < 0:
      agg["losses"] += 1

  block_symbols: List[str] = []
  promote_symbols = sorted(major_symbols())
  notes: List[str] = []

  for sym, agg in sorted(by_symbol.items()):
    if sym in major_symbols():
      continue
    if agg["trades"] >= min_trades and agg["pnl_usd"] <= -min_loss_usd:
      block_symbols.append(sym)
      notes.append(
        f"{sym}: {agg['trades']} trades, ${agg['pnl_usd']:,.2f} → block"
      )

  policy = {
    "updated_at": _utcnow(),
    "block_symbols": sorted(set(block_symbols) | env_blocklist()),
    "promote_symbols": promote_symbols,
    "symbol_stats": dict(by_symbol),
    "learn_notes": notes,
    "thresholds": {"min_trades": min_trades, "min_loss_usd": min_loss_usd},
  }
  out_path = _policy_path()
  out_path.parent.mkdir(parents=True, exist_ok=True)
  out_path.write_text(json.dumps(policy, indent=2, default=str), encoding="utf-8")
  return policy


def write_policy_report(policy: Optional[dict] = None) -> str:
  policy = policy or load_learned_policy()
  lines = [
    "# Paper Execution Policy (learned)",
    "",
    f"**Updated:** {policy.get('updated_at', 'n/a')}  ",
    "",
    "## Promote (majors first in sim queue)",
    "",
  ]
  for sym in policy.get("promote_symbols") or sorted(major_symbols()):
    lines.append(f"- {sym}")

  lines.extend(["", "## Block symbols", ""])
  for sym in policy.get("block_symbols") or sorted(symbol_blocklist()):
    stats = (policy.get("symbol_stats") or {}).get(sym, {})
    pnl = stats.get("pnl_usd", "—")
    n = stats.get("trades", "—")
    lines.append(f"- {sym} (n={n}, P&L ${pnl})")

  notes = policy.get("learn_notes") or []
  if notes:
    lines.extend(["", "## Learn notes", ""])
    for n in notes:
      lines.append(f"- {n}")

  lines.extend([
    "",
    f"> Policy: `{_policy_path()}` · Trades log: `{_trades_path()}`",
  ])
  text = "\n".join(lines) + "\n"
  out = _report_path()
  out.parent.mkdir(parents=True, exist_ok=True)
  out.write_text(text, encoding="utf-8")
  return text


def refresh_paper_policy() -> Dict[str, Any]:
  policy = learn_symbol_policy()
  write_policy_report(policy)
  return policy
