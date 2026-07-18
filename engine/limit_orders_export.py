"""Pair × timeframe GTC limit order export — staged tiers without changing honest gates."""

from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.risk import (
  DCA_SPLITS,
  build_dca_ladder,
  compute_wae,
  dynamic_stop,
  dynamic_targets,
  risk_package,
  stop_is_sane,
)
from engine.execution_advanced import (
  CONTINGENT_SYMBOLS,
  ExportContext,
  MacroState,
  build_contingent_scenarios,
  enrich_row_with_advanced,
  expand_contingent_rows,
  select_dca_profile,
)

ALL_TIMEFRAMES = ("1w", "1d", "4h", "1h", "15m")

# Maps each TF to the style that owns honest executable gates (4h is context-only).
TF_STYLE_MAP = {
  "15m": "scalp",
  "1h": "day_trade",
  "4h": None,
  "1d": "swing",
  "1w": "long_term",
}

TF_CONFIG: Dict[str, dict] = {
  "15m": {
    "horizon": "15m–4h",
    "atr_mult_sl": 0.8,
    "account_risk_pct": 0.5,
    "min_rr": 1.2,
    "max_stop_atr": 3.0,
  },
  "1h": {
    "horizon": "4h–2d",
    "atr_mult_sl": 1.2,
    "account_risk_pct": 0.75,
    "min_rr": 1.3,
    "max_stop_atr": 4.0,
  },
  "4h": {
    "horizon": "4h–3d",
    "atr_mult_sl": 1.5,
    "account_risk_pct": 0.85,
    "min_rr": 1.4,
    "max_stop_atr": 4.5,
  },
  "1d": {
    "horizon": "2d–4w",
    "atr_mult_sl": 1.8,
    "account_risk_pct": 1.0,
    "min_rr": 1.5,
    "max_stop_atr": 5.0,
  },
  "1w": {
    "horizon": "1w–6m",
    "atr_mult_sl": 2.5,
    "account_risk_pct": 1.5,
    "min_rr": 2.0,
    "max_stop_atr": 6.0,
  },
}

TIER_RISK_MULT = {"executable": 1.0, "monitor": 0.5, "watch": 0.25}
TIER_SIZE_CAP = {"executable": 100, "monitor": 50, "watch": 25}


def _dir_norm(d: str) -> str:
  return "LONG" if str(d).upper() in ("BULL", "LONG") else "SHORT"


def _fib_levels_from_kz(kz: dict) -> Optional[List[float]]:
  """Entry-zone fib prices only — never full HTF constituent cluster."""
  lo = float(kz.get("price_low") or 0)
  hi = float(kz.get("price_high") or 0)
  if lo > 0 and hi > 0 and lo < hi:
    return [lo, hi]
  return None


def _structure_bounds(wave: dict, fallback_price: float, atr: float) -> Tuple[float, float]:
  """Local structure from the last two waves on this TF."""
  waves = wave.get("waves_last5") or []
  if waves:
    pts: List[float] = []
    for w in waves[-2:]:
      for key in ("start", "end", "price_start", "price_end"):
        if key in w and w[key] is not None:
          pts.append(float(w[key]))
    if pts:
      return min(pts), max(pts)
  return fallback_price - 2 * atr, fallback_price + 2 * atr


def _resolve_stop(
  direction: str,
  entry: float,
  atr: float,
  s_low: float,
  s_high: float,
  cfg: dict,
  zone_low: float,
  zone_high: float,
  reused: Optional[dict] = None,
) -> dict:
  max_stop_atr = cfg.get("max_stop_atr", 5.0)
  if reused and isinstance(reused, dict) and reused.get("price") is not None:
    px = float(reused["price"])
    if stop_is_sane(direction, entry, px, atr, max_atr=max_stop_atr):
      return reused
  return dynamic_stop(
    direction, entry, atr, s_low, s_high, cfg["atr_mult_sl"],
    zone_low=zone_low, zone_high=zone_high, max_stop_atr=max_stop_atr,
  )


def _c_targets(result: dict) -> dict:
  return result.get("step3_c_targets") or result.get("step3_kill_zone") or {}


def _normalize_results(batch_or_results: Any) -> List[dict]:
  if isinstance(batch_or_results, list):
    return batch_or_results
  if isinstance(batch_or_results, dict):
    for key in ("pairs", "results", "instruments"):
      if key in batch_or_results and isinstance(batch_or_results[key], list):
        return batch_or_results[key]
  raise TypeError("expected list of results or batch dict with pairs/results key")


def _harmonic_for_tf(result: dict, tf: str) -> Optional[dict]:
  for h in result.get("step4_harmonic_overlap") or []:
    if h.get("tf") == tf:
      return h
  return None


def _resolve_gtc_tier(result: dict, tf: str) -> Tuple[str, str, str]:
  """
  Map honest setup status → GTC tier without mutating step8 outcomes.
  Returns (gtc_tier, honest_execution_tier, tier_note).
  """
  style = TF_STYLE_MAP.get(tf)
  setups = (result.get("step8_outcomes") or {}).get("setups") or {}
  if style and style in setups:
    setup = setups[style]
    st = setup.get("status", "not_actionable")
    tier = setup.get("execution_tier", "none")
    reason = setup.get("honest_reason", "")
    if st == "executable":
      return "executable", tier, reason
    if st == "monitor":
      return "monitor", "none", reason
    return "watch", "none", reason or f"{style} not_actionable — staged GTC only"

  wave = (result.get("step2_wave_structure") or {}).get(tf) or {}
  if _harmonic_for_tf(result, tf):
    return "monitor", "none", f"{tf} harmonic PRZ — staged GTC monitor tier"
  if wave.get("impulse_valid"):
    return "monitor", "none", f"{tf} impulse valid — staged GTC monitor tier"
  if wave.get("impulse_partial"):
    return "watch", "none", f"{tf} partial impulse — staged GTC watch tier"
  return "watch", "none", f"{tf} context TF — staged GTC watch tier"


def build_export_context(
  results: List[dict],
  *,
  account_equity: Optional[float] = None,
  usdt_d_pct: Optional[float] = None,
) -> ExportContext:
  high_beta = []
  for r in results:
    mkt = r.get("step9_market_confluence") or r.get("step9_market_tools") or {}
    bc = mkt.get("btc_correlation") or {}
    if bc.get("high_beta"):
      high_beta.append(r.get("symbol", "?"))
  return ExportContext(
    account_equity=account_equity,
    macro=MacroState(usdt_d_pct=usdt_d_pct),
    high_beta_symbols=high_beta,
  )


def _dca_to_columns(dca: List[dict]) -> Dict[str, Any]:
  """Map leg list to dca_10/20/30/40 CSV columns (2-layer uses L1→10%, L2→40%)."""
  cols: Dict[str, Any] = {}
  if len(dca) == 2:
    cols["dca_10pct_price"] = dca[0]["price"]
    cols["dca_10pct_size"] = dca[0]["size_pct"]
    cols["dca_20pct_price"] = ""
    cols["dca_20pct_size"] = ""
    cols["dca_30pct_price"] = ""
    cols["dca_30pct_size"] = ""
    cols["dca_40pct_price"] = dca[1]["price"]
    cols["dca_40pct_size"] = dca[1]["size_pct"]
    return cols
  slots = [10, 20, 30, 40]
  for i, leg in enumerate(dca[:4]):
    cols[f"dca_{slots[i]}pct_price"] = leg["price"]
    cols[f"dca_{slots[i]}pct_size"] = leg["size_pct"]
  return cols


def _gtc_dca_ladder(
  direction: str,
  anchor: float,
  atr: float,
  zone_low: float,
  zone_high: float,
  fib_levels: Optional[List[float]] = None,
  *,
  harmonic_prz: Optional[Tuple[float, float]] = None,
  profile: str = "pyramid_4",
) -> List[dict]:
  """Asymmetric pyramid — all GTC limits."""
  return build_dca_ladder(
    direction, anchor, atr, zone_low, zone_high, fib_levels,
    harmonic_prz=harmonic_prz, gtc=True, profile=profile,
  )


def _tier_account_risk(
  base_pct: float,
  gtc_tier: str,
  honest_tier: str,
  *,
  risk_ctx: Optional[dict] = None,
) -> float:
  mult = TIER_RISK_MULT.get(gtc_tier, 0.25)
  if gtc_tier == "executable" and honest_tier == "probe":
    mult *= 0.5
  if risk_ctx and risk_ctx.get("enabled"):
    from engine.dynamic_risk import apply_dynamic_account_risk

    return apply_dynamic_account_risk(base_pct * mult, risk_ctx)
  return round(base_pct * mult, 3)


def build_limit_order_row(
  result: dict,
  tf: str,
  ctx: Optional[ExportContext] = None,
) -> dict:
  """One GTC limit-order plan for symbol × timeframe."""
  if result.get("status") == "incomplete":
    return {
      "symbol": result.get("symbol"),
      "timeframe": tf,
      "status": "error",
      "error": result.get("error", "incomplete"),
    }

  cfg = TF_CONFIG[tf]
  style = TF_STYLE_MAP.get(tf) or f"{tf}_context"
  gtc_tier, honest_tier, tier_note = _resolve_gtc_tier(result, tf)

  ex = result.get("executive_decision") or {}
  consensus = result.get("step6_wave_consensus") or {}
  kz = result.get("step3_kill_zone") or {}
  ct = _c_targets(result)
  fib_levels = _fib_levels_from_kz(kz)
  kz_low = float(kz.get("price_low") or 0)
  kz_high = float(kz.get("price_high") or 0)
  in_zone = bool((result.get("step5_execution_validation") or {}).get("in_zone"))
  zone_low = kz_low
  zone_high = kz_high

  direction = _dir_norm(
    ex.get("direction")
    or (result.get("step8_outcomes") or {}).get("honest_summary", {}).get("primary_direction")
    or consensus.get("consensus_direction")
    or "LONG"
  )

  wave = (result.get("step2_wave_structure") or {}).get(tf) or {}
  pivots = (result.get("step2_adaptive_pivots") or {}).get(tf) or {}
  atr = float(pivots.get("atr_14") or 0)
  current = float(wave.get("current_price") or result.get("step1_htf_bias", {}).get("wave_C_current") or 0)
  if atr <= 0 and current > 0:
    atr = current * 0.01
  if current > 0 and atr > abs(current) * 0.15:
    atr = abs(current) * 0.01

  setups = (result.get("step8_outcomes") or {}).get("setups") or {}
  mapped_style = TF_STYLE_MAP.get(tf)
  reuse = setups.get(mapped_style) if mapped_style else None

  harm_tf = _harmonic_for_tf(result, tf)
  prz = _prz_tuple(harm_tf)

  # Reuse honest geometry when this TF owns the style setup (gates unchanged).
  if reuse and reuse.get("timeframe") == tf and reuse.get("entry"):
    entry_anchor = float(reuse["entry"]["anchor"])
    zone = reuse["entry"].get("zone") or [kz_low, kz_high]
    zone_low, zone_high = float(zone[0]), float(zone[1])
    readiness = reuse.get("readiness_score")
    indicators = "; ".join((reuse.get("indicator_signals") or [])[:3])
    honest_status = reuse.get("status")
    reused_stop = reuse.get("stop_loss")
  else:
    if harm_tf:
      zone_low, zone_high = float(harm_tf["prz_low"]), float(harm_tf["prz_high"])
      entry_anchor = (zone_low + zone_high) / 2
    elif in_zone:
      entry_anchor = current
      zone_low, zone_high = kz_low, kz_high
    else:
      entry_anchor = (kz_low + kz_high) / 2
      zone_low, zone_high = kz_low, kz_high
    readiness = None
    indicators = wave.get("structure", "")
    honest_status = "staged"
    reused_stop = None

  ctx = ctx or ExportContext()

  s_low, s_high = _structure_bounds(wave, current, atr)
  dca_profile, profile_reason = select_dca_profile(result["symbol"], tf, result, ctx)
  contingent = (
    build_contingent_scenarios(result, tf, cfg, ctx)
    if result["symbol"] in CONTINGENT_SYMBOLS and tf in ("1h", "4h")
    else None
  )

  dca = _gtc_dca_ladder(
    direction, entry_anchor, atr, zone_low, zone_high,
    fib_levels=fib_levels, harmonic_prz=prz, profile=dca_profile,
  )
  wae = compute_wae(dca)

  stop = _resolve_stop(
    direction, wae, atr, s_low, s_high, cfg, zone_low, zone_high, reused_stop,
  )
  targets = dynamic_targets(
    direction, wae, atr,
    harmonic_prz=prz,
    c_target_100=ct.get("c_target_100"),
    c_target_161=ct.get("c_target_161"),
  )

  while len(targets) < 3:
    targets.append(targets[-1] if targets else {"price": wae, "exit_pct": 0, "rr": 0})
  rr = targets[1].get("rr", 0) if len(targets) > 1 else 0

  risk_ctx: dict = {}
  try:
    from engine.dynamic_risk import compute_risk_multiplier
    from engine.outcome_tracker import load_metrics, lookup_win_rate

    metrics = load_metrics()
    wr, n = lookup_win_rate(metrics, result["symbol"], tf, direction)
    risk_ctx = compute_risk_multiplier(
      symbol=result["symbol"],
      timeframe=tf,
      direction=direction,
      readiness_score=int(readiness) if readiness is not None else None,
      hist_win_rate=wr,
      hist_n=n,
      gtc_tier=gtc_tier,
      honest_tier=honest_tier,
    )
  except Exception:
    pass

  acct_risk = _tier_account_risk(cfg["account_risk_pct"], gtc_tier, honest_tier, risk_ctx=risk_ctx)
  risk = risk_package(wae, stop["price"], acct_risk)
  size_cap = TIER_SIZE_CAP[gtc_tier]
  if gtc_tier == "executable" and honest_tier == "probe":
    size_cap = min(size_cap, 50)

  dca_cols = _dca_to_columns(dca)
  row = {
    "symbol": result["symbol"],
    "timeframe": tf,
    "style": style,
    "horizon": cfg["horizon"],
    "direction": direction,
    "row_type": "primary",
    "gtc_tier": gtc_tier,
    "gtc_size_cap_pct": size_cap,
    "honest_status": honest_status if mapped_style else "n/a",
    "honest_execution_tier": honest_tier,
    "readiness_score": readiness,
    "indicator_signals": indicators,
    "consensus": consensus.get("consensus_direction"),
    "agreement_pct": consensus.get("agreement_pct"),
    "executive_verdict": ex.get("verdict"),
    "in_kill_zone": "Y" if in_zone else "N",
    "wave_structure": wave.get("structure"),
    "wave_valid": "Y" if wave.get("impulse_valid") else "N",
    "entry_anchor": entry_anchor,
    "wae": wae,
    "dca_architecture": "asymmetric_pyramid_10_20_30_40",
    "entry_zone_low": zone_low,
    "entry_zone_high": zone_high,
    "dca_legs": dca,
    "dca_l1_rationale": dca[0].get("rationale", "") if dca else "",
    "dca_l2_rationale": dca[1].get("rationale", "") if len(dca) > 1 else "",
    "dca_l3_rationale": dca[2].get("rationale", "") if len(dca) > 2 else "",
    "dca_l4_rationale": dca[3].get("rationale", "") if len(dca) > 3 else "",
    **dca_cols,
    "stop_loss": stop["price"],
    "stop_rule": stop.get("rule"),
    "stop_distance_pct": stop.get("distance_pct"),
    "tp1": targets[0]["price"],
    "tp1_exit_pct": targets[0]["exit_pct"],
    "tp2": targets[1]["price"],
    "tp2_exit_pct": targets[1]["exit_pct"],
    "tp3": targets[2]["price"],
    "tp3_exit_pct": targets[2]["exit_pct"],
    "rr_tp2": rr,
    "min_rr": cfg["min_rr"],
    "account_risk_pct": acct_risk,
    "dynamic_risk_mult": risk_ctx.get("mult"),
    "dynamic_risk_factors": "; ".join(risk_ctx.get("factors", [])),
    "risk_sizing_rule": risk["sizing_rule"],
    "order_type": "limit",
    "time_in_force": "GTC",
    "tier_note": tier_note,
    "playbook": _playbook_line(gtc_tier, honest_tier, direction, tf, dca, stop, targets, wae),
  }

  if ctx and ctx.historical_metrics:
    from engine.outcome_tracker import apply_feedback_to_row
    row = apply_feedback_to_row(row, ctx.historical_metrics)

  row = enrich_row_with_advanced(row, dca, ctx, dca_profile, profile_reason, contingent)
  if contingent:
    row["contingent_scenarios_json"] = json.dumps(
      [{"id": s["scenario_id"], "trigger": s["scenario_trigger"], "direction": s["direction"], "wae": s["wae"]} for s in contingent],
      default=str,
    )
  return row


def _prz_tuple(harm: Optional[dict]) -> Optional[Tuple[float, float]]:
  if not harm:
    return None
  return float(harm["prz_low"]), float(harm["prz_high"])


def _playbook_line(
  gtc_tier: str,
  honest_tier: str,
  direction: str,
  tf: str,
  dca: List[dict],
  stop: dict,
  targets: List[dict],
  wae: float,
) -> str:
  legs = ", ".join(f"{l.get('layer', 'L'+str(l['leg']))} {l['size_pct']}%@{l['price']}" for l in dca)
  tier_lbl = gtc_tier.upper()
  if gtc_tier == "executable" and honest_tier == "probe":
    tier_lbl = "EXECUTABLE_PROBE"
  return (
    f"{tier_lbl} {direction} {tf}: asymmetric DCA [{legs}] · WAE {wae} · "
    f"hard SL {stop['price']} · TP {targets[0]['price']}/{targets[1]['price']}/{targets[2]['price']}"
  )


def build_all_limit_orders(
  results: List[dict],
  tfs: Optional[List[str]] = None,
  ctx: Optional[ExportContext] = None,
) -> List[dict]:
  """250+ rows for n_pairs × 5 TFs; contingent scenarios add child rows."""
  tfs = list(tfs or ALL_TIMEFRAMES)
  ctx = ctx or build_export_context(results)
  rows: List[dict] = []
  for result in results:
    for tf in tfs:
      primary = build_limit_order_row(result, tf, ctx)
      rows.append(primary)
      contingent = primary.get("contingent_scenarios")
      if contingent:
        rows.extend(expand_contingent_rows(primary, contingent))
  return rows


def _serialize_rows_for_csv(rows: List[dict]) -> List[dict]:
  out = []
  for r in rows:
    row = dict(r)
    if "contingent_scenarios" in row:
      del row["contingent_scenarios"]
    if isinstance(row.get("dca_legs"), list):
      row["dca_legs"] = json.dumps(row["dca_legs"], default=str)
    out.append(row)
  return out


def save_limit_orders_csv(rows: List[dict], path: str | Path) -> str:
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  if not rows:
    path.write_text("")
    return str(path)
  keys: List[str] = []
  seen = set()
  for row in rows:
    for k in row:
      if k not in seen:
        seen.add(k)
        keys.append(k)
  with path.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
  return str(path)


def _matrix_cell_class(row: dict) -> str:
  if row.get("status") == "error":
    return "err"
  tier = row.get("gtc_tier", "")
  honest = row.get("honest_execution_tier", "")
  if tier == "executable" and honest == "full":
    return "exec-full"
  if tier == "executable":
    return "exec-probe"
  if tier == "monitor":
    return "mon"
  if tier == "watch":
    return "watch"
  return "na"


def _matrix_cell_html(row: Optional[dict]) -> str:
  if not row or row.get("status") == "error":
    return '<td class="na"><span class="empty">—</span></td>'

  def _usd(v) -> str:
    try:
      f = float(v)
      return f"${f:,.0f}" if f > 0 else ""
    except (TypeError, ValueError):
      return ""

  tier = row.get("gtc_tier", "")
  honest = row.get("honest_execution_tier", "")
  direction = row.get("direction", "")
  tier_label = tier
  if tier == "executable" and honest == "full":
    tier_label = "FULL"
  elif tier == "executable" and honest == "probe":
    tier_label = "PROBE"

  wae = row.get("wae", "")
  risk = row.get("risk_budget_usd", "")
  profile = row.get("dca_profile", "")

  lines = [
    f'<strong>{html.escape(direction)}</strong> · {html.escape(str(tier_label))}',
    f'WAE {html.escape(str(wae))}',
  ]
  l1_usd = row.get("leg1_usd")
  l1_px = row.get("dca_10pct_price")
  if l1_usd:
    try:
      if float(l1_usd) > 0:
        lines.append(html.escape(f"L1 {_usd(l1_usd)}"))
    except (TypeError, ValueError):
      pass
  elif l1_px:
    lines.append(html.escape(f"L1 @ {l1_px}"))
  if risk:
    lines.append(html.escape(f"Risk {_usd(risk)}"))
  if profile and profile != "pyramid_4":
    lines.append(f'<span class="profile">{html.escape(profile)}</span>')

  cls = _matrix_cell_class(row)
  return f'<td class="{cls}"><div class="cell">{"<br/>".join(lines)}</div></td>'


def save_limit_orders_matrix_html(
  rows: List[dict],
  path: str | Path,
  *,
  title: str = "Trade Setups — All Pairs × Timeframes",
  account_equity: Optional[float] = None,
) -> str:
  """Shaded pair×TF matrix — primary rows only, color by GTC tier."""
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)

  primary = [r for r in rows if r.get("row_type", "primary") == "primary" and r.get("symbol")]
  if not primary:
    path.write_text(f"<html><body><h1>{html.escape(title)}</h1><p>No data</p></body></html>")
    return str(path)

  by_sym: Dict[str, Dict[str, dict]] = {}
  for r in primary:
    by_sym.setdefault(r["symbol"], {})[r["timeframe"]] = r

  tier_ctr: Dict[str, int] = {}
  for r in primary:
    key = _matrix_cell_class(r)
    tier_ctr[key] = tier_ctr.get(key, 0) + 1

  symbols = sorted(by_sym.keys())
  tfs = list(ALL_TIMEFRAMES)
  ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
  equity_line = f" · ${account_equity:,.0f} equity" if account_equity else ""

  header = "".join(f"<th>{html.escape(tf)}</th>" for tf in tfs)
  body_rows = []
  for sym in symbols:
    cells = "".join(_matrix_cell_html(by_sym[sym].get(tf)) for tf in tfs)
    body_rows.append(
      f'<tr><th class="sym">{html.escape(sym)}</th>{cells}</tr>'
    )

  doc = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; margin: 1rem; background: #fafafa; }}
  h1 {{ font-size: 1.35rem; margin-bottom: 0.25rem; }}
  .meta {{ color: #555; margin-bottom: 1rem; font-size: 0.9rem; }}
  .legend {{ margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; }}
  .legend span {{ padding: 4px 10px; border-radius: 4px; font-size: 0.8rem; border: 1px solid #ccc; }}
  .wrap {{ overflow: auto; max-width: 100%; border: 1px solid #bbb; border-radius: 6px; background: #fff; }}
  table {{ border-collapse: collapse; font-size: 11px; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 0; vertical-align: top; }}
  th.sym {{ position: sticky; left: 0; z-index: 2; background: #1a1a2e; color: #eee; padding: 6px 8px; white-space: nowrap; min-width: 100px; }}
  thead th {{ background: #1a1a2e; color: #eee; padding: 8px 6px; position: sticky; top: 0; z-index: 3; }}
  thead th:first-child {{ z-index: 4; left: 0; }}
  td .cell {{ padding: 6px 8px; line-height: 1.35; min-width: 110px; }}
  td.exec-full {{ background: #2e7d32; color: #fff; }}
  td.exec-probe {{ background: #c8e6c9; color: #1b5e20; }}
  td.mon {{ background: #fff8e1; color: #5d4037; }}
  td.watch {{ background: #f5f5f5; color: #616161; }}
  td.err {{ background: #ffcdd2; color: #b71c1c; }}
  td.na {{ background: #fafafa; color: #999; }}
  .profile {{ font-size: 9px; opacity: 0.85; }}
  .empty {{ padding: 6px 8px; display: block; text-align: center; }}
</style>
</head><body>
<h1>{html.escape(title)}</h1>
<p class="meta">{len(symbols)} pairs × {len(tfs)} timeframes = {len(primary)} cells · {ts}{equity_line}</p>
<div class="legend">
  <span style="background:#2e7d32;color:#fff">FULL executable ({tier_ctr.get('exec-full', 0)})</span>
  <span style="background:#c8e6c9;color:#1b5e20">PROBE executable ({tier_ctr.get('exec-probe', 0)})</span>
  <span style="background:#fff8e1;color:#5d4037">monitor ({tier_ctr.get('mon', 0)})</span>
  <span style="background:#f5f5f5;color:#616161">watch ({tier_ctr.get('watch', 0)})</span>
</div>
<div class="wrap"><table>
<thead><tr><th>Symbol</th>{header}</tr></thead>
<tbody>{"".join(body_rows)}</tbody>
</table></div>
</body></html>"""
  path.write_text(doc, encoding="utf-8")
  return str(path)


def export_limit_orders(
  batch_or_results: Any,
  output_dir: str | Path = "output",
  *,
  timestamp: Optional[str] = None,
  write_json: bool = False,
  account_equity: Optional[float] = None,
  usdt_d_pct: Optional[float] = None,
) -> dict:
  """Write pair×TF GTC limit order CSV + JSON summary."""
  output_dir = Path(output_dir)
  results = _normalize_results(batch_or_results)
  from engine.outcome_tracker import resolve_open_setups, compute_metrics, save_metrics, record_setups, save_performance_report

  resolved = resolve_open_setups(is_crypto=True)
  metrics = compute_metrics()
  metrics["last_resolved"] = resolved
  save_metrics(metrics)
  save_performance_report(metrics)

  ctx = build_export_context(results, account_equity=account_equity, usdt_d_pct=usdt_d_pct)
  ctx.historical_metrics = metrics
  ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  rows = build_all_limit_orders(results, ctx=ctx)

  recorded = record_setups(rows)
  metrics["newly_recorded"] = recorded
  save_metrics(metrics)

  tier_ctr: Dict[str, int] = {}
  tf_ctr: Dict[str, int] = {}
  for r in rows:
    tier = r.get("gtc_tier", "?")
    tier_ctr[tier] = tier_ctr.get(tier, 0) + 1
    tf = r.get("timeframe", "?")
    tf_ctr[tf] = tf_ctr.get(tf, 0) + 1

  csv_path = output_dir / f"limit_orders_all_tf_{ts}.csv"
  stable_csv = output_dir / "latest_limit_orders_all_tf.csv"
  serializable = _serialize_rows_for_csv(rows)
  save_limit_orders_csv(serializable, csv_path)
  save_limit_orders_csv(serializable, stable_csv)
  matrix_html = output_dir / "latest_trade_setups_matrix.html"
  save_limit_orders_matrix_html(
    rows, matrix_html, title="Trade Setups — All Pairs × Timeframes",
    account_equity=account_equity,
  )

  meta = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "row_count": len(rows),
    "expected_rows": 50 * len(ALL_TIMEFRAMES),
    "pairs": len({r["symbol"] for r in rows if r.get("symbol")}),
    "timeframes": list(ALL_TIMEFRAMES),
    "tier_counts": tier_ctr,
    "tf_counts": tf_ctr,
    "by_gtc_tier": tier_ctr,
    "csv": str(csv_path),
    "latest_csv": str(stable_csv),
    "stable_csv": str(stable_csv),
    "matrix_html": str(matrix_html),
    "dca_splits_pct": DCA_SPLITS,
    "account_equity": account_equity,
    "usdt_d_pct": usdt_d_pct,
    "macro": ctx.macro_eval,
    "high_beta_symbols": ctx.high_beta_symbols,
    "contingent_rows": sum(1 for r in rows if r.get("row_type") == "contingent_scenario"),
    "historical_learning": {
      "resolved": resolved,
      "newly_recorded": recorded,
      "overall_win_rate": metrics.get("overall", {}).get("win_rate"),
      "open_tracked": metrics.get("open_count"),
      "closed_tracked": metrics.get("closed_count"),
    },
  }
  meta_path = output_dir / "autodream" / "latest_limit_orders.json"
  meta_path.parent.mkdir(parents=True, exist_ok=True)
  meta_path.write_text(json.dumps(meta, indent=2))

  if write_json:
    json_path = output_dir / f"limit_orders_all_tf_{ts}.json"
    json_path.write_text(json.dumps(rows, indent=2, default=str))
    meta["json"] = str(json_path)

  return meta


def load_results_from_json(path: str | Path) -> List[dict]:
  return json.loads(Path(path).read_text())
