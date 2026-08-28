#!/usr/bin/env python3
"""Export complete pair×TF trade setups markdown from latest limit orders CSV."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

TFS = ["1w", "1d", "4h", "1h", "15m"]


def _fmt_price(v: float) -> str:
  if v <= 0:
    return "—"
  if v < 0.01:
    return f"{v:.6g}"
  if v < 1:
    return f"{v:.4f}"
  if v < 1000:
    return f"{v:.2f}"
  return f"{v:,.2f}"


def _cell(r: dict | None) -> str:
  if not r:
    return "—"
  d = "L" if r.get("direction") == "LONG" else "S"
  v = (r.get("executive_verdict") or "?")[:6]
  t = (r.get("gtc_tier") or "?")[:4]
  wae = _fmt_price(float(r.get("wae") or 0))
  l1 = r.get("leg1_usd")
  l1s = f"${float(l1):.0f}" if l1 and float(l1) > 0 else "—"
  return f"**{d}** {v}/{t}<br>WAE {wae}<br>L1 {l1s}"


def export_md(csv_path: Path, out_path: Path) -> dict:
  rows = [r for r in csv.DictReader(csv_path.open()) if r.get("row_type", "primary") == "primary"]
  by_sym: dict[str, dict[str, dict]] = {}
  for r in rows:
    by_sym.setdefault(r["symbol"], {})[r["timeframe"]] = r

  symbols = sorted(by_sym.keys())
  ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
  tier_ctr = Counter(r.get("gtc_tier") for r in rows)
  verdict_ctr = Counter(r.get("executive_verdict") for r in rows)
  exec_rows = [r for r in rows if r.get("gtc_tier") == "executable"]

  lines = [
    "# Complete Trade Setups — All Pairs × Timeframes",
    "",
    f"**Updated:** {ts} · **Pairs:** {len(symbols)} · **Cells:** {len(rows)}",
    "",
    "## Summary",
    "",
    "| GTC tier | Count |",
    "|----------|-------|",
  ]
  for k, v in sorted(tier_ctr.items(), key=lambda x: -x[1]):
    lines.append(f"| {k} | {v} |")
  lines += ["", "| Executive verdict | Count |", "|-------------------|-------|"]
  for k, v in sorted(verdict_ctr.items(), key=lambda x: -x[1]):
    lines.append(f"| {k} | {v} |")
  lines += [
    "",
    f"**Executable GTC rows:** {len(exec_rows)}",
    "",
    "## Matrix (all pairs × timeframes)",
    "",
    "| Symbol | 1w | 1d | 4h | 1h | 15m |",
    "|--------|----|----|----|----|-----|",
  ]
  for sym in symbols:
    cells = " | ".join(_cell(by_sym[sym].get(tf)) for tf in TFS)
    lines.append(f"| {sym} | {cells} |")

  lines += [
    "",
    "## Full detail (every pair × TF)",
    "",
  ]
  for sym in symbols:
    lines.append(f"### {sym}")
    lines.append("")
    for tf in TFS:
      r = by_sym[sym].get(tf)
      if not r:
        lines.append(f"- **{tf}:** —")
        continue
      lines.append(
        f"- **{tf}** · {r.get('direction')} · `{r.get('executive_verdict')}` · "
        f"GTC `{r.get('gtc_tier')}` · honest `{r.get('honest_execution_tier')}` · "
        f"readiness {r.get('readiness_score') or '—'}"
      )
      lines.append(
        f"  - WAE {_fmt_price(float(r.get('wae') or 0))} · "
        f"SL {_fmt_price(float(r.get('stop_loss') or 0))} · "
        f"TP1 {_fmt_price(float(r.get('tp1') or 0))} · "
        f"R:R {r.get('rr_tp2') or '—'}"
      )
      legs = []
      for i in range(1, 5):
        px = r.get(f"dca_{[10,20,30,40][i-1]}pct_price")
        usd = r.get(f"leg{i}_usd")
        if px and str(px).strip():
          legs.append(f"L{i}@{px} (${usd or '—'})")
      if legs:
        lines.append(f"  - DCA: {', '.join(legs)}")
      lines.append(f"  - {str(r.get('tier_note') or r.get('playbook') or '')[:120]}")
    lines.append("")

  out_path.parent.mkdir(parents=True, exist_ok=True)
  out_path.write_text("\n".join(lines), encoding="utf-8")
  return {
    "pairs": len(symbols),
    "rows": len(rows),
    "executable": len(exec_rows),
    "out": str(out_path),
  }


def main() -> None:
  p = argparse.ArgumentParser()
  p.add_argument("--csv", default="output/latest_limit_orders_all_tf.csv")
  p.add_argument("--out", default="output/COMPLETE_TRADE_SETUPS_PAIR_TF.md")
  args = p.parse_args()
  meta = export_md(Path(args.csv), Path(args.out))
  print(meta)


if __name__ == "__main__":
  main()
