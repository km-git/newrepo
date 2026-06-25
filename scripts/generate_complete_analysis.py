#!/usr/bin/env python3
"""Generate COMPLETE_TRADING_ANALYSIS.md with dollar-sized leg amounts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.limit_orders_export import ALL_TIMEFRAMES, export_limit_orders

TF_ORDER = list(ALL_TIMEFRAMES)


def _usd(v) -> str:
    if v in (None, "", "0", 0):
        return "—"
    try:
        f = float(v)
        return "—" if f <= 0 else f"${f:,.2f}"
    except (TypeError, ValueError):
        return "—"


def _leg_usd_summary(r: dict) -> str:
    raw = r.get("dca_legs") or ""
    if raw:
        try:
            legs = json.loads(raw)
            parts = []
            for leg in legs:
                i = int(leg.get("leg") or len(parts) + 1)
                key = f"leg{i}_usd"
                if r.get(key) and float(r[key] or 0) > 0:
                    parts.append(
                        f"L{i} {_usd(r[key])} ({leg.get('size_pct')}% @ {leg.get('price')})"
                    )
            if parts:
                return " · ".join(parts)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    parts = []
    pcts = [10, 20, 30, 40]
    for i in range(1, 5):
        key = f"leg{i}_usd"
        if r.get(key) and float(r[key] or 0) > 0:
            p = r.get(f"dca_{pcts[i - 1]}pct_price", "")
            s = r.get(f"dca_{pcts[i - 1]}pct_size", "")
            parts.append(f"L{i} {_usd(r[key])} ({s}% @ {p})")
    return " · ".join(parts) if parts else "—"


def build_markdown(
    batch_path: Path,
    limits_rows: list[dict],
    *,
    equity: float,
    usdt_d: float | None,
) -> str:
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    batch_by_sym = {r["symbol"]: r for r in batch}

    primary = [r for r in limits_rows if r.get("row_type", "primary") == "primary"]
    contingent = [r for r in limits_rows if r.get("row_type") == "contingent_scenario"]

    by_sym: dict[str, list] = defaultdict(list)
    for r in primary:
        by_sym[r["symbol"]].append(r)
    for sym in by_sym:
        by_sym[sym].sort(key=lambda x: TF_ORDER.index(x["timeframe"]))

    tier_ctr = Counter(r["gtc_tier"] for r in primary)
    exec_rows = [r for r in primary if r["gtc_tier"] == "executable"]

    in_zone = sum(1 for r in batch if (r.get("step5_execution_validation") or {}).get("in_zone"))
    by_consensus = Counter((r.get("step6_wave_consensus") or {}).get("consensus_direction", "?") for r in batch)
    by_verdict = Counter((r.get("executive_decision") or {}).get("verdict", "?") for r in batch)
    setup_status: Counter = Counter()
    for r in batch:
        for s in (r.get("step8_outcomes") or {}).get("setups", {}).values():
            setup_status[s.get("status", "?")] += 1

    macro_mode = limits_rows[0].get("macro_mode", "NEUTRAL") if limits_rows else "NEUTRAL"
    macro_note = limits_rows[0].get("macro_note", "") if limits_rows else ""

    lines: list[str] = []
    lines.append("# Complete Trading Analysis — Top 50 Crypto")
    lines.append("")
    lines.append(f"**Batch:** `{batch_path.name}`  ")
    lines.append(f"**Account equity:** **${equity:,.2f}**  ")
    if usdt_d is not None:
        lines.append(f"**USDT.D:** {usdt_d}% → macro **{macro_mode}**  ")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Pairs analyzed | {len(batch)} |")
    lines.append(f"| Primary rows (pair×TF) | {len(primary)} |")
    lines.append(f"| Contingent scenario rows | {len(contingent)} |")
    lines.append(f"| Total export rows | {len(limits_rows)} |")
    lines.append(f"| In kill zone | {in_zone}/{len(batch)} |")
    lines.append(f"| Consensus BULL / BEAR | {by_consensus.get('BULL', 0)} / {by_consensus.get('BEAR', 0)} |")
    lines.append(f"| Executable | {tier_ctr.get('executable', 0)} |")
    lines.append(f"| Monitor | {tier_ctr.get('monitor', 0)} |")
    lines.append(f"| Watch | {tier_ctr.get('watch', 0)} |")
    lines.append("")
    lines.append(f"**Macro:** {macro_note}")
    lines.append("")
    lines.append(
        f"**Sizing:** Leg USD = position notional × leg %; "
        f"notional from risk budget ÷ |WAE−SL| × WAE @ **${equity:,.0f}** equity."
    )
    lines.append("")
    lines.append("### Executive verdicts")
    for v, c in sorted(by_verdict.items(), key=lambda x: -x[1]):
        lines.append(f"- **{v}:** {c}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## Executable Book ({len(exec_rows)} rows) — @ ${equity:,.0f}")
    lines.append("")
    lines.append("| Symbol | TF | Tier | Dir | WAE | Risk $ | Notional $ | Leg USD | SL | TP2 |")
    lines.append("|--------|-----|------|-----|-----|--------|------------|---------|-----|-----|")
    for r in sorted(exec_rows, key=lambda x: (x["symbol"], TF_ORDER.index(x["timeframe"]))):
        tier = r.get("honest_execution_tier", "")
        if tier == "full":
            tier = "FULL"
        elif tier == "probe":
            tier = "PROBE"
        legs = _leg_usd_summary(r)
        if len(legs) > 80:
            legs = legs[:77] + "..."
        lines.append(
            f"| {r['symbol']} | {r['timeframe']} | {tier} | {r['direction']} | {r['wae']} "
            f"| {_usd(r.get('risk_budget_usd'))} | {_usd(r.get('position_notional_usd'))} "
            f"| {legs} | {r['stop_loss']} | {r['tp2']} |"
        )
    lines.append("")
    if contingent:
        lines.append("---")
        lines.append("")
        lines.append("## Contingent Dual Scenarios (BTC/ETH)")
        lines.append("")
        for r in sorted(contingent, key=lambda x: (x["symbol"], x["timeframe"], x.get("scenario_id", ""))):
            lines.append(f"### {r['symbol']} {r['timeframe']} — `{r.get('scenario_id')}` ({r['direction']})")
            lines.append("")
            lines.append(f"**Trigger:** {r.get('scenario_trigger', '')}")
            lines.append("")
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")
            lines.append(f"| Profile | {r.get('dca_profile', '')} |")
            lines.append(f"| WAE | {r['wae']} |")
            lines.append(f"| Risk budget | {_usd(r.get('risk_budget_usd'))} |")
            lines.append(f"| Position notional | {_usd(r.get('position_notional_usd'))} |")
            lines.append(f"| L1 (10%) | {r.get('dca_10pct_price')} → {_usd(r.get('leg1_usd'))} |")
            lines.append(f"| L2 (90%) | {r.get('dca_40pct_price')} → {_usd(r.get('leg2_usd'))} |")
            lines.append(f"| Hard stop | {r['stop_loss']} |")
            lines.append(f"| TP1 / TP2 / TP3 | {r['tp1']} / {r['tp2']} / {r['tp3']} |")
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## All Pairs — Full Setup Tables @ ${equity:,.0f}")
    lines.append("")
    for sym in sorted(by_sym.keys()):
        br = batch_by_sym.get(sym, {})
        ex = br.get("executive_decision") or {}
        cons = br.get("step6_wave_consensus") or {}
        kz = br.get("step3_kill_zone") or {}
        in_z = (br.get("step5_execution_validation") or {}).get("in_zone", False)
        summary = (br.get("step8_outcomes") or {}).get("honest_summary") or {}

        lines.append(f"### {sym}")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Verdict | {ex.get('verdict', '')} |")
        lines.append(f"| Direction | {ex.get('direction', '')} |")
        lines.append(f"| Consensus | {cons.get('consensus_direction', '')} ({cons.get('agreement_pct', '')}%) |")
        lines.append(f"| Kill zone | {kz.get('price_low', '')} – {kz.get('price_high', '')} |")
        lines.append(f"| In zone | {'Yes' if in_z else 'No'} |")
        lines.append(f"| Honest summary | {summary.get('truth', '')} |")
        lines.append("")
        lines.append(
            "| TF | Tier | Profile | Dir | WAE | Risk $ | Notional $ | "
            "L1 $ | L2 $ | L3 $ | L4 $ | SL | TP1 | TP2 | TP3 |"
        )
        lines.append("|----|------|---------|-----|-----|--------|------------|------|------|------|------|-----|-----|-----|-----|")
        for row in by_sym[sym]:
            tier = row["gtc_tier"]
            if row.get("honest_execution_tier") == "full":
                tier += " F"
            elif row.get("honest_execution_tier") == "probe" and tier == "executable":
                tier += " P"
            lines.append(
                f"| {row['timeframe']} | {tier} | {row.get('dca_profile', '')} | {row['direction']} "
                f"| {row['wae']} | {_usd(row.get('risk_budget_usd'))} | {_usd(row.get('position_notional_usd'))} "
                f"| {_usd(row.get('leg1_usd'))} | {_usd(row.get('leg2_usd'))} | {_usd(row.get('leg3_usd'))} | {_usd(row.get('leg4_usd'))} "
                f"| {row['stop_loss']} | {row['tp1']} | {row['tp2']} | {row['tp3']} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate COMPLETE_TRADING_ANALYSIS.md")
    ap.add_argument("--input", type=Path, default=None, help="Batch JSON")
    ap.add_argument("--output", type=Path, default=ROOT / "output" / "COMPLETE_TRADING_ANALYSIS.md")
    ap.add_argument("--output-dir", type=Path, default=ROOT / "output")
    ap.add_argument("--equity", type=float, default=50_000.0, help="Account equity USD")
    ap.add_argument("--usdt-d", type=float, default=None, dest="usdt_d", help="USDT.D %%")
    args = ap.parse_args()

    if args.input is None:
        candidates = sorted(
            args.output_dir.glob("top50_analysis_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            print("No batch JSON found", file=sys.stderr)
            return 1
        args.input = candidates[0]

    batch = json.loads(args.input.read_text(encoding="utf-8"))
    export_limit_orders(
        batch, output_dir=args.output_dir,
        account_equity=args.equity, usdt_d_pct=args.usdt_d,
    )
    limits = list(csv.DictReader((args.output_dir / "latest_limit_orders_all_tf.csv").open()))
    md = build_markdown(args.input, limits, equity=args.equity, usdt_d=args.usdt_d)
    args.output.write_text(md, encoding="utf-8")
    print(f"Wrote {args.output} ({len(md.splitlines())} lines) @ ${args.equity:,.2f} equity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
