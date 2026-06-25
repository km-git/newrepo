"""Advanced execution: DCA profiles, macro switch, contingent scenarios, dollar sizing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.risk import (
  DCA_PROFILE_10_90,
  build_dca_ladder,
  compute_wae,
  dynamic_stop,
  dynamic_targets,
)

def _r(x: float, decimals: int = 6) -> float:
  return round(float(x), decimals)

DEFAULT_MACRO_LONG_UPGRADE_PCT = 8.45
DEFAULT_MACRO_NUKE_PCT = 8.953

DCA_PROFILE_PYRAMID = "pyramid_4"
DCA_PROFILE_10_90 = "two_layer_10_90"
DCA_PROFILE_30_70 = "two_layer_30_70"

CONTINGENT_SYMBOLS = frozenset({"BTC/USDT", "ETH/USDT"})
CORRELATION_CAP_SYMBOLS = frozenset({
  "ADA/USDT", "PENGU/USDT", "PI/USDT", "DOGE/USDT", "SOL/USDT",
  "AVAX/USDT", "LINK/USDT", "NEAR/USDT",
})


@dataclass
class MacroState:
  usdt_d_pct: Optional[float] = None
  long_upgrade_pct: float = DEFAULT_MACRO_LONG_UPGRADE_PCT
  nuke_pct: float = DEFAULT_MACRO_NUKE_PCT

  def evaluate(self) -> dict:
    if self.usdt_d_pct is None:
      return {
        "mode": "NEUTRAL",
        "long_boost_pct": 0.0,
        "cancel_longs": False,
        "flip_crypto_short": False,
        "note": "USDT.D not supplied — macro switch inactive",
      }
    v = float(self.usdt_d_pct)
    if v >= self.nuke_pct:
      return {
        "mode": "NUKE",
        "long_boost_pct": 0.0,
        "cancel_longs": True,
        "flip_crypto_short": True,
        "note": f"USDT.D {v}% ≥ nuke tick {self.nuke_pct}% — cancel longs, flip BTC/ETH short",
      }
    if v <= self.long_upgrade_pct:
      return {
        "mode": "LONG_UPGRADE",
        "long_boost_pct": 10.0,
        "cancel_longs": False,
        "flip_crypto_short": False,
        "note": f"USDT.D {v}% ≤ upgrade tick {self.long_upgrade_pct}% — crypto long layers +10%",
      }
    return {
      "mode": "NEUTRAL",
      "long_boost_pct": 0.0,
      "cancel_longs": False,
      "flip_crypto_short": False,
      "note": f"USDT.D {v}% between upgrade and nuke — no macro override",
    }


@dataclass
class ExportContext:
  account_equity: Optional[float] = None
  macro: MacroState = field(default_factory=MacroState)
  high_beta_symbols: List[str] = field(default_factory=list)

  @property
  def macro_eval(self) -> dict:
    return self.macro.evaluate()


def _btc_corr(result: dict) -> float:
  mkt = result.get("step9_market_confluence") or result.get("step9_market_tools") or {}
  corr = (mkt.get("btc_correlation") or {}).get("correlation")
  return abs(float(corr)) if corr is not None else 0.0


def select_dca_profile(symbol: str, tf: str, result: dict, ctx: ExportContext) -> Tuple[str, str]:
  corr = _btc_corr(result)
  if symbol in CONTINGENT_SYMBOLS and tf in ("1h", "4h"):
    return DCA_PROFILE_10_90, "PTJ contingent cap — dual-scenario 10/90 two-layer"
  if corr >= 0.7 and symbol in CORRELATION_CAP_SYMBOLS and tf in ("1d", "1w"):
    return DCA_PROFILE_30_70, f"Dalio correlation cap — |BTC corr| {corr:.2f}, 30/70 two-layer"
  if corr >= 0.85 and tf in ("1d", "1w"):
    return DCA_PROFILE_30_70, f"high-beta |BTC corr| {corr:.2f} — 30/70 two-layer"
  return DCA_PROFILE_PYRAMID, "standard asymmetric pyramid 10/20/30/40"


def apply_macro_to_row(row: dict, ctx: ExportContext) -> dict:
  macro = ctx.macro_eval
  row = dict(row)
  row["macro_mode"] = macro["mode"]
  row["macro_note"] = macro["note"]
  sym = row.get("symbol", "")
  direction = row.get("direction", "")
  if macro["cancel_longs"] and direction == "LONG":
    row["gtc_tier"] = "watch"
    row["tier_note"] = f"MACRO NUKE — long cancelled · {row.get('tier_note', '')}"
    row["gtc_size_cap_pct"] = 0
    row["account_risk_pct"] = 0
  if macro["flip_crypto_short"] and sym in CONTINGENT_SYMBOLS and direction == "LONG":
    row["gtc_tier"] = "watch"
    row["tier_note"] = f"MACRO NUKE — flip short preferred · {row.get('tier_note', '')}"
  if macro["long_boost_pct"] and direction == "LONG" and row.get("gtc_tier") == "executable":
    boost = float(macro["long_boost_pct"])
    row["macro_long_boost_pct"] = boost
    base = float(row.get("account_risk_pct") or 0)
    row["account_risk_pct"] = round(base * (1 + boost / 100), 3)
  return row


def compute_leg_dollars(
  equity: float,
  legs: List[dict],
  wae: float,
  stop: float,
  account_risk_pct: float,
  gtc_size_cap_pct: float,
  *,
  macro_long_boost_pct: float = 0.0,
) -> dict:
  cap = max(0.0, min(100.0, float(gtc_size_cap_pct))) / 100.0
  risk_pct = float(account_risk_pct) / 100.0
  if macro_long_boost_pct:
    risk_pct *= 1 + float(macro_long_boost_pct) / 100.0
  risk_budget_usd = equity * risk_pct * cap
  risk_per_unit = abs(float(wae) - float(stop))
  if risk_per_unit <= 0 or wae <= 0:
    return {
      "account_equity": equity,
      "risk_budget_usd": round(risk_budget_usd, 2),
      "position_units": 0,
      "position_notional_usd": 0,
      "leg_usd": {},
    }
  units = risk_budget_usd / risk_per_unit
  notional = units * float(wae)
  leg_usd = {f"leg{leg['leg']}_usd": round(notional * float(leg["size_pct"]) / 100.0, 2) for leg in legs}
  return {
    "account_equity": equity,
    "risk_budget_usd": round(risk_budget_usd, 2),
    "position_units": round(units, 6),
    "position_notional_usd": round(notional, 2),
    "leg_usd": leg_usd,
  }


def _manual_two_layer_dca(
  direction: str,
  l1_price: float,
  l2_price: float,
  splits: List[int],
  *,
  gtc: bool = True,
  profile: str = DCA_PROFILE_10_90,
) -> List[dict]:
  labels = ["L1", "L2"]
  legs = []
  for i, (label, pct) in enumerate(zip(labels, splits)):
    px = _r(l1_price if i == 0 else l2_price)
    legs.append({
      "leg": i + 1,
      "layer": label,
      "size_pct": pct,
      "price": px,
      "rationale": "contingent probe" if i == 0 else "contingent max conviction",
      "order_type": "limit",
      "time_in_force": "GTC" if gtc else "IOC",
      "trigger": f"GTC limit @ {px}",
      "profile": profile,
    })
  wae = compute_wae(legs)
  for leg in legs:
    leg["wae"] = wae
  return legs


def build_contingent_scenarios(result: dict, tf: str, cfg: dict, ctx: ExportContext) -> List[dict]:
  if result.get("symbol") not in CONTINGENT_SYMBOLS:
    return []
  kz = result.get("step3_kill_zone") or {}
  kz_lo = float(kz.get("price_low") or 0)
  kz_hi = float(kz.get("price_high") or 0)
  wave = (result.get("step2_wave_structure") or {}).get(tf) or {}
  pivots = (result.get("step2_adaptive_pivots") or {}).get(tf) or {}
  atr = float(pivots.get("atr_14") or 0)
  current = float(wave.get("current_price") or result.get("step1_htf_bias", {}).get("wave_C_current") or 0)
  if atr <= 0 and current > 0:
    atr = current * 0.01
  s_low, s_high = kz_lo, kz_hi
  waves = wave.get("waves_last5") or []
  if waves:
    w = waves[-1]
    s_low = min(float(w.get("start", kz_lo)), float(w.get("end", kz_lo)))
    s_high = max(float(w.get("start", kz_hi)), float(w.get("end", kz_hi)))

  short_l1 = kz_hi if kz_hi > 0 else current
  short_l2 = kz_lo if kz_lo > 0 else short_l1 - atr
  short_dca = _manual_two_layer_dca("SHORT", short_l1, short_l2, [10, 90])
  short_wae = compute_wae(short_dca)
  short_stop = dynamic_stop(
    "SHORT", short_wae, atr, s_low, s_high, cfg["atr_mult_sl"],
    zone_low=kz_lo, zone_high=kz_hi, max_stop_atr=cfg.get("max_stop_atr", 5.0),
  )
  short_targets = dynamic_targets("SHORT", short_wae, atr)

  long_l1 = kz_lo if kz_lo > 0 else current
  long_l2 = long_l1 - max(atr * 1.5, (kz_hi - kz_lo) if kz_hi > kz_lo else atr)
  long_dca = _manual_two_layer_dca("LONG", long_l1, long_l2, [10, 90])
  long_wae = compute_wae(long_dca)
  long_stop = dynamic_stop(
    "LONG", long_wae, atr, s_low, s_high, cfg["atr_mult_sl"],
    zone_low=long_l2, zone_high=kz_hi, max_stop_atr=cfg.get("max_stop_atr", 5.0),
  )
  long_targets = dynamic_targets("LONG", long_wae, atr)

  return [
    {
      "scenario_id": "short_breakdown",
      "scenario_trigger": f"fires if {short_l1} ticks first (breakdown node)",
      "direction": "SHORT",
      "dca_profile": DCA_PROFILE_10_90,
      "dca": short_dca,
      "wae": short_wae,
      "stop": short_stop,
      "targets": short_targets,
      "entry_anchor": short_l1,
      "zone_low": short_l2,
      "zone_high": short_l1,
    },
    {
      "scenario_id": "long_floor",
      "scenario_trigger": f"fires if {long_l1} ticks first (structural floor)",
      "direction": "LONG",
      "dca_profile": DCA_PROFILE_10_90,
      "dca": long_dca,
      "wae": long_wae,
      "stop": long_stop,
      "targets": long_targets,
      "entry_anchor": long_l1,
      "zone_low": long_l2,
      "zone_high": kz_hi or long_l1,
    },
  ]


def enrich_row_with_advanced(
  row: dict,
  legs: List[dict],
  ctx: ExportContext,
  dca_profile: str,
  profile_reason: str,
  contingent_scenarios: Optional[List[dict]] = None,
) -> dict:
  row = apply_macro_to_row(row, ctx)
  row["dca_profile"] = dca_profile
  row["dca_profile_reason"] = profile_reason
  macro = ctx.macro_eval
  boost = float(row.get("macro_long_boost_pct") or macro.get("long_boost_pct") or 0)
  if ctx.account_equity and float(ctx.account_equity) > 0:
    sizing = compute_leg_dollars(
      float(ctx.account_equity), legs, float(row["wae"]), float(row["stop_loss"]),
      float(row.get("account_risk_pct") or 0), float(row.get("gtc_size_cap_pct") or 100),
      macro_long_boost_pct=boost if row.get("direction") == "LONG" else 0,
    )
    row["account_equity"] = sizing["account_equity"]
    row["risk_budget_usd"] = sizing["risk_budget_usd"]
    row["position_notional_usd"] = sizing["position_notional_usd"]
    row["position_units"] = sizing["position_units"]
    for k, v in sizing["leg_usd"].items():
      row[k] = v
  if contingent_scenarios:
    row["order_mode"] = "contingent_dual"
    row["contingent_scenarios"] = contingent_scenarios
  else:
    row["order_mode"] = "single"
  return row


def dca_legs_to_columns(dca: List[dict]) -> Dict[str, Any]:
  if len(dca) == 2:
    return {
      "dca_10pct_price": dca[0]["price"],
      "dca_10pct_size": dca[0]["size_pct"],
      "dca_20pct_price": "",
      "dca_20pct_size": "",
      "dca_30pct_price": "",
      "dca_30pct_size": "",
      "dca_40pct_price": dca[1]["price"],
      "dca_40pct_size": dca[1]["size_pct"],
    }
  slots = [10, 20, 30, 40]
  return {f"dca_{slots[i]}pct_price": leg["price"] for i, leg in enumerate(dca[:4])} | {
    f"dca_{slots[i]}pct_size": leg["size_pct"] for i, leg in enumerate(dca[:4])
  }


def expand_contingent_rows(base_row: dict, scenarios: List[dict]) -> List[dict]:
  children: List[dict] = []
  for sc in scenarios:
    child = {k: v for k, v in base_row.items() if k not in ("contingent_scenarios", "dca_legs")}
    child["row_type"] = "contingent_scenario"
    child["scenario_id"] = sc["scenario_id"]
    child["scenario_trigger"] = sc["scenario_trigger"]
    child["direction"] = sc["direction"]
    child["dca_profile"] = sc["dca_profile"]
    child["order_mode"] = "contingent_dual"
    child["entry_anchor"] = sc["entry_anchor"]
    child["entry_zone_low"] = sc["zone_low"]
    child["entry_zone_high"] = sc["zone_high"]
    child["wae"] = sc["wae"]
    child["stop_loss"] = sc["stop"]["price"]
    child["stop_rule"] = sc["stop"].get("rule")
    child["tp1"] = sc["targets"][0]["price"]
    child["tp2"] = sc["targets"][1]["price"]
    child["tp3"] = sc["targets"][2]["price"]
    child.update(dca_legs_to_columns(sc["dca"]))
    children.append(child)
  return children
