"""Portfolio risk manager — concurrent caps and account risk limits."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from engine.paper_trading import PAPER_LEDGER_PATH

DEFAULT_MAX_CONCURRENT = 8
DEFAULT_MAX_SMC_CONCURRENT = 4
DEFAULT_MAX_ACCOUNT_RISK_PCT = 4.0
DEFAULT_MAX_SYMBOL_EXPOSURE_PCT = 1.5

STATE_PATH = Path("output/autodream/portfolio_state.json")


def _load_ledger(path: Path = PAPER_LEDGER_PATH) -> List[dict]:
  if not path.exists():
    return []
  rows: List[dict] = []
  with path.open() as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      try:
        rows.append(json.loads(line))
      except json.JSONDecodeError:
        continue
  return rows


def open_positions(ledger: Optional[List[dict]] = None) -> List[dict]:
  """Trades without a closed outcome are treated as open."""
  ledger = ledger if ledger is not None else _load_ledger()
  open_rows: List[dict] = []
  for t in ledger:
    outcome = t.get("paper_outcome")
    if outcome in ("win", "loss"):
      continue
    if t.get("available") is False:
      continue
    open_rows.append(t)
  return open_rows


def account_risk_exposure(
  positions: Optional[List[dict]] = None,
  ledger: Optional[List[dict]] = None,
) -> float:
  """Sum of size_factor × stop risk proxy for open positions."""
  positions = positions if positions is not None else open_positions(ledger)
  total = 0.0
  for p in positions:
    size = float(p.get("size_factor") or p.get("cohort_size_pct", 0) / 100 or 0)
    stop_pct = float(p.get("stop_pct") or 0.75)
    total += size * stop_pct / 100
  return round(total, 3)


def _symbol_exposure(symbol: str, positions: List[dict]) -> float:
  total = 0.0
  for p in positions:
    if p.get("symbol") != symbol:
      continue
    size = float(p.get("size_factor") or p.get("cohort_size_pct", 0) / 100 or 0)
    total += size
  return total


def approve_candidates(
  candidates: List[dict],
  *,
  open_pos: Optional[List[dict]] = None,
  max_concurrent: int = DEFAULT_MAX_CONCURRENT,
  max_smc_concurrent: int = DEFAULT_MAX_SMC_CONCURRENT,
  max_account_risk_pct: float = DEFAULT_MAX_ACCOUNT_RISK_PCT,
  max_symbol_exposure_pct: float = DEFAULT_MAX_SYMBOL_EXPOSURE_PCT,
) -> Tuple[List[dict], List[dict]]:
  """
  Filter execution candidates by portfolio limits.
  Returns (approved, rejected_with_reason).
  """
  open_pos = open_pos if open_pos is not None else open_positions()
  current_risk = account_risk_exposure(open_pos)
  open_count = len(open_pos)
  smc_open = sum(1 for p in open_pos if p.get("style") == "smc")

  approved: List[dict] = []
  rejected: List[dict] = []

  for c in candidates:
    sym = c.get("symbol", "")
    style = c.get("style", "")
    size_pct = float(c.get("calibrated_size_pct") or c.get("position_size_pct") or 0)
    stop_pct = float(c.get("stop_pct") or 0.75)
    risk_add = size_pct * stop_pct / 100

    reasons: List[str] = []
    if open_count + len(approved) >= max_concurrent:
      reasons.append(f"max_concurrent={max_concurrent}")
    if style == "smc" and smc_open + sum(1 for a in approved if a.get("style") == "smc") >= max_smc_concurrent:
      reasons.append(f"max_smc_concurrent={max_smc_concurrent}")
    if current_risk + sum(
      float(a.get("calibrated_size_pct") or a.get("position_size_pct") or 0)
      * float(a.get("stop_pct") or 0.75) / 100
      for a in approved
    ) + risk_add > max_account_risk_pct:
      reasons.append(f"account_risk>{max_account_risk_pct}%")
    sym_exp = _symbol_exposure(sym, open_pos) + _symbol_exposure(sym, approved)
    if sym_exp + size_pct / 100 > max_symbol_exposure_pct:
      reasons.append(f"symbol_exposure>{max_symbol_exposure_pct}%")

    if any(k in c for k in ("symbol", "style")) and sym and (sym, style) in {
      (p.get("symbol"), p.get("style")) for p in open_pos
    }:
      reasons.append("duplicate_open_position")

    if reasons:
      rejected.append({**c, "reject_reason": "; ".join(reasons)})
      continue

    approved.append({**c, "portfolio_approved": True})
    open_count += 1
    if style == "smc":
      smc_open += 1
    current_risk += risk_add

  return approved, rejected


def save_portfolio_state(
  approved: List[dict],
  rejected: List[dict],
  path: str | Path = STATE_PATH,
) -> dict:
  path = Path(path)
  payload = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "open_count": len(open_positions()),
    "account_risk_pct": account_risk_exposure(),
    "approved": approved,
    "rejected": rejected,
  }
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(payload, indent=2, default=str))
  return payload
