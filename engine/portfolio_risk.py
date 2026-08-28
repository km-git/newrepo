"""Portfolio heat, correlation-aware sizing, and hedge recommendations.

Implements institutional portfolio-risk controls:
- Total portfolio heat cap (default 6% of equity)
- Correlated-cluster heat cap (default 3% per driver)
- Correlation shrink on overlapping exposure
- Hedge plans when EW engines diverge or macro risk rises

Research basis: portfolio heat limits (Elder 6% rule), correlation clustering
(Elliott Wave cross-market confirmation), delta-neutral hedging for carry/basis
when directional conviction is mixed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.execution_advanced import CORRELATION_CAP_SYMBOLS, CONTINGENT_SYMBOLS, resolve_account_equity

STATE_PATH = Path(os.environ.get("EW_PORTFOLIO_STATE", "output/execution/portfolio_state.json"))

BTC_CLUSTER = frozenset({"BTC/USDT"})
ETH_CLUSTER = frozenset({"ETH/USDT"})
HIGH_BETA_CLUSTER = frozenset(CORRELATION_CAP_SYMBOLS) | frozenset({
  "DOGE/USDT", "PEPE/USDT", "SUI/USDT", "WLD/USDT", "ENA/USDT",
})


def portfolio_risk_enabled() -> bool:
  return os.environ.get("EW_PORTFOLIO_RISK", "1").lower() not in ("0", "false", "no")


def max_portfolio_heat_pct() -> float:
  return float(os.environ.get("EW_PORTFOLIO_HEAT_PCT", "6"))


def max_cluster_heat_pct() -> float:
  return float(os.environ.get("EW_CLUSTER_HEAT_PCT", "3"))


def hedge_enabled() -> bool:
  return os.environ.get("EW_HEDGE_RECOMMEND", "1").lower() not in ("0", "false", "no")


def symbol_cluster(symbol: str) -> str:
  sym = (symbol or "").upper()
  if sym in BTC_CLUSTER:
    return "btc"
  if sym in ETH_CLUSTER:
    return "eth"
  if sym in HIGH_BETA_CLUSTER:
    return "high_beta"
  if sym.endswith("/USDT") and sym.startswith(("XAU", "XAUT", "PAXG")):
    return "stable"
  return "alt"


def correlation_shrink(rho: float) -> float:
  """Pairwise shrink: 1 / sqrt(1 + rho). rho in [0, 1]."""
  rho = max(0.0, min(1.0, abs(float(rho))))
  return round(1.0 / (1.0 + rho) ** 0.5, 3)


def row_risk_pct(row: dict, equity: Optional[float] = None) -> float:
  """Risk at stop as % of account equity."""
  eq = resolve_account_equity(equity or row.get("account_equity"))
  if eq <= 0:
    return 0.0
  try:
    budget = float(row.get("risk_budget_usd") or 0)
    if budget > 0:
      return round(budget / eq * 100, 4)
    risk_pct = float(row.get("account_risk_pct") or 0)
    cap = float(row.get("gtc_size_cap_pct") or 100) / 100.0
    return round(risk_pct * cap, 4)
  except (TypeError, ValueError):
    return 0.0


@dataclass
class PortfolioState:
  equity: float = 10_000.0
  total_heat_pct: float = 0.0
  cluster_heat: Dict[str, float] = field(default_factory=dict)
  long_heat_pct: float = 0.0
  short_heat_pct: float = 0.0
  open_count: int = 0
  positions: List[dict] = field(default_factory=list)

  def to_dict(self) -> dict:
    return {
      "equity": self.equity,
      "total_heat_pct": round(self.total_heat_pct, 3),
      "cluster_heat": {k: round(v, 3) for k, v in self.cluster_heat.items()},
      "long_heat_pct": round(self.long_heat_pct, 3),
      "short_heat_pct": round(self.short_heat_pct, 3),
      "open_count": self.open_count,
      "positions": self.positions,
    }


def compute_portfolio_state(
  rows: List[dict],
  *,
  equity: Optional[float] = None,
  only_open: bool = True,
) -> PortfolioState:
  """Aggregate portfolio heat from export rows or open position records."""
  eq = resolve_account_equity(equity)
  state = PortfolioState(equity=eq)
  for row in rows:
    if only_open and row.get("status") in ("closed_sl", "closed_tp", "closed"):
      continue
    if row.get("gtc_tier") not in (None, "executable") and row.get("honest_status") not in ("executable",):
      if only_open and not row.get("open"):
        continue
    risk = row_risk_pct(row, eq)
    if risk <= 0:
      continue
    cluster = symbol_cluster(row.get("symbol", ""))
    direction = str(row.get("direction", "")).upper()
    state.total_heat_pct += risk
    state.cluster_heat[cluster] = state.cluster_heat.get(cluster, 0.0) + risk
    if direction in ("LONG", "BULL"):
      state.long_heat_pct += risk
    elif direction in ("SHORT", "BEAR"):
      state.short_heat_pct += risk
    state.open_count += 1
    state.positions.append({
      "symbol": row.get("symbol"),
      "timeframe": row.get("timeframe"),
      "direction": direction,
      "risk_pct": risk,
      "cluster": cluster,
    })
  return state


def portfolio_heat_multiplier(state: PortfolioState, row: dict) -> Tuple[float, List[str]]:
  """Shrink new-entry size when portfolio/cluster heat is elevated."""
  if not portfolio_risk_enabled():
    return 1.0, []

  mult = 1.0
  factors: List[str] = []
  max_heat = max_portfolio_heat_pct()
  max_cluster = max_cluster_heat_pct()
  proposed = row_risk_pct(row, state.equity)
  projected = state.total_heat_pct + proposed

  if projected >= max_heat:
    mult *= 0.0
    factors.append(f"portfolio heat {projected:.1f}% ≥ cap {max_heat}% → block")
    return mult, factors

  utilization = state.total_heat_pct / max_heat if max_heat > 0 else 0
  if utilization >= 0.85:
    mult *= 0.50
    factors.append(f"portfolio heat {state.total_heat_pct:.1f}% at {utilization:.0%} cap → ×0.50")
  elif utilization >= 0.65:
    mult *= 0.75
    factors.append(f"portfolio heat {state.total_heat_pct:.1f}% elevated → ×0.75")

  cluster = symbol_cluster(row.get("symbol", ""))
  cluster_heat = state.cluster_heat.get(cluster, 0.0) + proposed
  if cluster_heat >= max_cluster:
    mult *= 0.0
    factors.append(f"cluster {cluster} heat {cluster_heat:.1f}% ≥ cap {max_cluster}% → block")
  elif cluster_heat >= max_cluster * 0.8:
    mult = min(mult, 0.60)
    factors.append(f"cluster {cluster} heat {cluster_heat:.1f}% near cap → ×0.60")

  # Net directional imbalance — long book heavy in risk-off macro
  direction = str(row.get("direction", "")).upper()
  if direction in ("LONG", "BULL") and state.long_heat_pct > state.short_heat_pct * 2.5:
    if state.long_heat_pct >= max_heat * 0.5:
      mult = min(mult, 0.70)
      factors.append(f"long book heat {state.long_heat_pct:.1f}% dominant → ×0.70")

  # Correlation shrink when adding to same cluster
  same_cluster = [p for p in state.positions if p.get("cluster") == cluster]
  if same_cluster:
    rho = 0.75 if cluster in ("btc", "eth", "high_beta") else 0.55
    shrink = correlation_shrink(rho)
    mult *= shrink
    factors.append(f"corr shrink ρ={rho:.2f} → ×{shrink}")

  return round(max(0.0, min(1.0, mult)), 3), factors


def gate_portfolio_heat(row: dict, state: Optional[PortfolioState] = None) -> Tuple[bool, List[str]]:
  """Pre-execution gate: block when heat caps breached."""
  if not portfolio_risk_enabled():
    return True, []
  state = state or load_portfolio_state()
  mult, factors = portfolio_heat_multiplier(state, row)
  if mult <= 0:
    return False, factors
  return True, factors


def recommend_hedge(
  *,
  symbol: str,
  direction: str,
  consensus: Optional[dict] = None,
  macro_mode: str = "NEUTRAL",
  in_zone: bool = False,
  execution_passes: bool = False,
  btc_correlation: Optional[float] = None,
  portfolio_state: Optional[PortfolioState] = None,
) -> dict:
  """
  Build actionable hedge plan when conviction is mixed or portfolio is skewed.

  Strategies (advisory — execution depends on broker perp support):
  1. partial_probe — reduce directional size when engines disagree
  2. btc_perp_hedge — short BTC perp vs long high-beta alt (delta overlay)
  3. contingent_dual — use existing long_floor/short_breakdown scenarios
  4. portfolio_rebalance — trim long heat when cluster cap approached
  """
  if not hedge_enabled():
    return {"enabled": False, "strategies": [], "recommended_size_pct": 100}

  consensus = consensus or {}
  agreement = float(consensus.get("agreement_pct") or 0)
  divergences = list(consensus.get("divergences") or [])
  strategies: List[dict] = []
  size_pct = 100

  # Engine divergence → partial probe + optional hedge overlay
  if agreement < 60 or divergences:
    size_pct = min(size_pct, 50)
    strategies.append({
      "id": "partial_probe",
      "action": "reduce_directional_size",
      "size_pct": 50,
      "rationale": f"EW agreement {agreement:.0f}% with divergences — probe only",
      "trigger": "immediate",
    })
    if symbol in CONTINGENT_SYMBOLS:
      strategies.append({
        "id": "contingent_dual",
        "action": "deploy_dual_scenario_orders",
        "rationale": "BTC/ETH: use long_floor + short_breakdown contingent book",
        "trigger": "first_touch_node",
      })
    elif btc_correlation and abs(btc_correlation) >= 0.7 and direction.upper() in ("LONG", "BULL"):
      hedge_ratio = round(min(0.70, abs(btc_correlation)), 2)
      strategies.append({
        "id": "btc_perp_hedge",
        "action": "short_btc_perp_overlay",
        "hedge_ratio": hedge_ratio,
        "instrument": "BTC/USDT perpetual",
        "rationale": (
          f"High-beta long with |BTC corr| {abs(btc_correlation):.2f} — "
          f"short {hedge_ratio:.0%} notional via perp to cut directional delta"
        ),
        "trigger": "on_primary_fill",
        "exit_trigger": "funding_rate < 0.005% for 2 periods OR primary TP1 hit",
      })

  if not execution_passes and in_zone:
    size_pct = min(size_pct, 50)
    strategies.append({
      "id": "micro_confirm",
      "action": "wait_15m_impulse",
      "size_pct": 50,
      "rationale": "15m impulse unvalidated — add second 50% only on structure confirm",
      "trigger": "15m_impulse_valid",
    })

  if macro_mode == "NUKE":
    size_pct = 0
    strategies.append({
      "id": "macro_nuke_flat",
      "action": "cancel_longs_prefer_short",
      "rationale": "USDT.D nuke tick — flatten long bias, flip BTC/ETH short preferred",
      "trigger": "immediate",
    })
  elif macro_mode == "LONG_UPGRADE" and direction.upper() in ("LONG", "BULL"):
    strategies.append({
      "id": "macro_long_boost",
      "action": "allow_long_layers",
      "boost_pct": 10,
      "rationale": "USDT.D upgrade tick — crypto long risk +10% within heat cap",
      "trigger": "immediate",
    })

  state = portfolio_state or load_portfolio_state()
  if state.total_heat_pct >= max_portfolio_heat_pct() * 0.7:
    size_pct = min(size_pct, 35)
    strategies.append({
      "id": "portfolio_heat_trim",
      "action": "cap_new_entry",
      "size_pct": 35,
      "rationale": f"Portfolio heat {state.total_heat_pct:.1f}% — trim new entry size",
      "trigger": "immediate",
    })

  if state.long_heat_pct > max_portfolio_heat_pct() and direction.upper() in ("LONG", "BULL"):
    strategies.append({
      "id": "long_book_hedge",
      "action": "add_short_overlay_or_pause_longs",
      "rationale": f"Long book heat {state.long_heat_pct:.1f}% — hedge or pause new longs",
      "trigger": "before_next_long_entry",
    })

  # Funding carry note when hedge would be delta-neutral
  if any(s["id"] == "btc_perp_hedge" for s in strategies):
    strategies.append({
      "id": "funding_monitor",
      "action": "monitor_perp_funding",
      "rationale": "Delta-neutral overlay: exit hedge if funding turns negative 2 consecutive periods",
      "trigger": "funding_rate_reversal",
    })

  return {
    "enabled": True,
    "recommended_size_pct": size_pct,
    "strategies": strategies,
    "portfolio_heat_pct": round(state.total_heat_pct, 2),
    "cluster_heat": {k: round(v, 2) for k, v in state.cluster_heat.items()},
  }


def apply_hedge_to_executive(executive: dict, hedge: dict) -> dict:
  """Merge hedge plan into executive_decision contingencies and size."""
  if not hedge.get("enabled"):
    return executive
  ex = dict(executive)
  rec_size = int(hedge.get("recommended_size_pct") or 100)
  if rec_size < ex.get("position_size_pct", 100):
    ex["position_size_pct"] = rec_size
    ex.setdefault("structural_gaps", []).append(
      f"hedge overlay caps size at {rec_size}%"
    )
  contingencies = list(ex.get("contingencies") or [])
  for strat in hedge.get("strategies", []):
    contingencies.append({
      "if": strat.get("trigger", "condition"),
      "then": f"{strat['id']}: {strat.get('action', '')} — {strat.get('rationale', '')}",
    })
  ex["contingencies"] = contingencies[:12]
  ex["hedge_plan"] = hedge
  return ex


def apply_portfolio_risk_to_row(
  row: dict,
  state: Optional[PortfolioState] = None,
  *,
  update_state: bool = False,
) -> dict:
  """Apply portfolio heat multiplier to row sizing fields."""
  if not portfolio_risk_enabled():
    return row
  state = state or PortfolioState(equity=resolve_account_equity(row.get("account_equity")))
  mult, factors = portfolio_heat_multiplier(state, row)
  if mult >= 1.0 and not factors:
    return row
  row = dict(row)
  if mult <= 0:
    row["gtc_tier"] = "watch"
    row["gtc_size_cap_pct"] = 0
    row["portfolio_heat_block"] = True
    row["portfolio_risk_note"] = "; ".join(factors)
    return row
  cap = float(row.get("gtc_size_cap_pct") or 100)
  new_cap = round(cap * mult, 1)
  row["gtc_size_cap_pct"] = new_cap
  base_risk = float(row.get("account_risk_pct") or 0)
  row["account_risk_pct"] = round(base_risk * mult, 4)
  row["portfolio_heat_mult"] = mult
  existing = str(row.get("dynamic_risk_factors") or "")
  row["dynamic_risk_factors"] = "; ".join(filter(None, [existing, "; ".join(factors)]))
  row["portfolio_risk_note"] = "; ".join(factors)
  if update_state and mult > 0:
    risk = row_risk_pct(row, state.equity)
    cluster = symbol_cluster(row.get("symbol", ""))
    state.total_heat_pct += risk
    state.cluster_heat[cluster] = state.cluster_heat.get(cluster, 0.0) + risk
    direction = str(row.get("direction", "")).upper()
    if direction in ("LONG", "BULL"):
      state.long_heat_pct += risk
    elif direction in ("SHORT", "BEAR"):
      state.short_heat_pct += risk
    state.open_count += 1
  return row


def load_portfolio_state() -> PortfolioState:
  """Load persisted open-position heat or derive from paper sim / export."""
  if STATE_PATH.exists():
    try:
      data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
      return PortfolioState(
        equity=float(data.get("equity") or resolve_account_equity()),
        total_heat_pct=float(data.get("total_heat_pct") or 0),
        cluster_heat=dict(data.get("cluster_heat") or {}),
        long_heat_pct=float(data.get("long_heat_pct") or 0),
        short_heat_pct=float(data.get("short_heat_pct") or 0),
        open_count=int(data.get("open_count") or 0),
        positions=list(data.get("positions") or []),
      )
    except Exception:
      pass
  # Fallback: derive from paper sim open trades
  paper_path = Path(os.environ.get("EW_PAPER_PNL_JSON", "output/execution/paper_pnl.json"))
  if paper_path.exists():
    try:
      data = json.loads(paper_path.read_text(encoding="utf-8"))
      open_rows = [t for t in data.get("trades", []) if t.get("status") == "open"]
      if open_rows:
        return compute_portfolio_state(open_rows, equity=data.get("ending_equity"))
    except Exception:
      pass
  return PortfolioState(equity=resolve_account_equity())


def save_portfolio_state(state: PortfolioState) -> None:
  STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
  STATE_PATH.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def portfolio_risk_status() -> dict:
  """CLI/API status snapshot."""
  state = load_portfolio_state()
  return {
    "enabled": portfolio_risk_enabled(),
    "hedge_recommend": hedge_enabled(),
    "max_portfolio_heat_pct": max_portfolio_heat_pct(),
    "max_cluster_heat_pct": max_cluster_heat_pct(),
    "state": state.to_dict(),
    "headroom_pct": round(max(0, max_portfolio_heat_pct() - state.total_heat_pct), 2),
    "halted": state.total_heat_pct >= max_portfolio_heat_pct(),
  }


def augment_analysis_with_portfolio_risk(
  decision: dict,
  *,
  symbol: str,
  consensus: Optional[dict] = None,
  macro_mode: str = "NEUTRAL",
  in_zone: bool = False,
  execution_passes: bool = False,
  btc_correlation: Optional[float] = None,
) -> dict:
  """Augment executive_decide() output with hedge plan and portfolio context."""
  if not portfolio_risk_enabled() and not hedge_enabled():
    return decision
  state = load_portfolio_state()
  hedge = recommend_hedge(
    symbol=symbol,
    direction=decision.get("executive_decision", {}).get("direction", ""),
    consensus=consensus,
    macro_mode=macro_mode,
    in_zone=in_zone,
    execution_passes=execution_passes,
    btc_correlation=btc_correlation,
    portfolio_state=state,
  )
  decision = dict(decision)
  decision["executive_decision"] = apply_hedge_to_executive(
    decision.get("executive_decision", {}), hedge
  )
  decision["portfolio_risk"] = {
    "heat_pct": state.total_heat_pct,
    "headroom_pct": round(max(0, max_portfolio_heat_pct() - state.total_heat_pct), 2),
    "hedge": hedge,
  }
  return decision
