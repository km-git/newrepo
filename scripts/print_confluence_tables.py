#!/usr/bin/env python3
"""Print full confluence tables — all pairs × styles × SMC per-TF."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

STYLES = ("scalp", "day_trade", "swing", "long_term", "smc")
STYLE_TF = {"scalp": "15m", "day_trade": "1h", "swing": "1d", "long_term": "1w", "smc": "15m"}
TFS = ("15m", "1h", "4h", "1d", "1w")


def find_latest() -> Path:
  files = sorted(Path("output").glob("top50_analysis_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
  if not files:
    raise FileNotFoundError("No top50_analysis_*.json — run scripts/run_top50_batch.py")
  return files[0]


def _tags_short(tags: list, n: int = 3) -> str:
  if not tags:
    return "—"
  return "; ".join(str(t) for t in tags[:n])


def build_setup_rows(results: list) -> list[dict]:
  rows = []
  for r in results:
    if r.get("status") == "incomplete":
      rows.append({
        "symbol": r.get("symbol", "?"),
        "style": "—",
        "tf": "—",
        "status": "incomplete",
        "tier": "—",
        "dir": "—",
        "grade": "—",
        "conf": "—",
        "signal": "—",
        "probe": "—",
        "score": "—",
        "oos": "—",
        "confluence": "—",
        "paper": "—",
      })
      continue
    sym = r["symbol"]
    setups = (r.get("step8_outcomes") or {}).get("setups", {})
    for style in STYLES:
      s = setups.get(style) or {}
      tf = s.get("timeframe") or STYLE_TF.get(style, "—")
      tags = s.get("indicator_signals") or (s.get("indicators") or {}).get("active_tokens") or []
      rows.append({
        "symbol": sym,
        "style": style,
        "tf": tf,
        "status": s.get("status", "—"),
        "tier": s.get("execution_tier", "—"),
        "dir": s.get("direction", "—"),
        "grade": s.get("entry_grade") or "—",
        "conf": s.get("confluence_count") if s.get("confluence_count") is not None else "—",
        "signal": "Y" if s.get("entry_signal") else ("—" if style != "smc" else "N"),
        "probe": "Y" if s.get("entry_probe") else "—",
        "score": s.get("readiness_score") or s.get("institutional_score") or "—",
        "oos": f"{float(s['oos_win_rate']):.0%}" if s.get("oos_win_rate") is not None else "—",
        "confluence": _tags_short(tags, 4),
        "paper": s.get("paper_outcome") or "—",
      })
  return rows


def build_smc_tf_rows(results: list) -> list[dict]:
  """SMC institutional confluence per timeframe (15m, 1h, 4h)."""
  rows = []
  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    smc = (r.get("step8_outcomes") or {}).get("setups", {}).get("smc") or {}
    inst = smc.get("institutional") or {}
    by_tf = inst.get("by_tf") or {}
    for tf in ("15m", "1h", "4h"):
      t = by_tf.get(tf) or {}
      if t.get("status") not in ("ok",):
        rows.append({
          "symbol": sym, "tf": tf, "score": "—", "grade": "—",
          "conf": "—", "signal": "—", "probe": "—", "vp": "—",
          "confluence": "no data",
        })
        continue
      tags = t.get("tags") or []
      rows.append({
        "symbol": sym,
        "tf": tf,
        "score": t.get("score", "—"),
        "grade": t.get("entry_grade", "—"),
        "conf": f"{t.get('partial_confluence', 0)}/3",
        "signal": "Y" if t.get("entry_signal") else "N",
        "probe": "Y" if t.get("entry_probe") else "N",
        "vp": "Y" if t.get("vp_filter_ok") else "N",
        "confluence": _tags_short(tags, 5),
      })
  return rows


def build_pair_summary(results: list) -> list[dict]:
  rows = []
  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    ex = r.get("executive_decision") or {}
    cons = r.get("step6_wave_consensus") or {}
    smc = (r.get("step8_outcomes") or {}).get("setups", {}).get("smc") or {}
    board = None
    for p in (json.loads(Path("output/autodream/executive_board.json").read_text()).get("picks", [])
              if Path("output/autodream/executive_board.json").exists() else []):
      if p.get("symbol") == sym and p.get("style") == "smc":
        board = p
        break
    rows.append({
      "symbol": sym,
      "pipeline": r.get("status", "—"),
      "verdict": ex.get("verdict", "—"),
      "consensus": cons.get("consensus_direction", "—"),
      "agree": f"{cons.get('agreement_pct', 0):.0f}%",
      "smc_status": smc.get("status", "—"),
      "smc_grade": smc.get("entry_grade", "—"),
      "smc_conf": smc.get("confluence_count", "—"),
      "smc_signal": "Y" if smc.get("entry_signal") else "N",
      "smc_tf": smc.get("timeframe", "—"),
      "exec_action": board.get("executive_action", "—") if board else "—",
    })
  return rows


def print_md_table(headers: list[str], rows: list[dict], keys: list[str], max_rows: int | None = None) -> None:
  subset = rows[:max_rows] if max_rows else rows
  print("| " + " | ".join(headers) + " |")
  print("| " + " | ".join("---" for _ in headers) + " |")
  for row in subset:
    cells = []
    for k in keys:
      v = row.get(k, "—")
      s = str(v).replace("|", "/")[:48]
      cells.append(s)
    print("| " + " | ".join(cells) + " |")
  if max_rows and len(rows) > max_rows:
    print(f"\n*({len(rows) - max_rows} more rows — see CSV export)*")


def save_csv(path: Path, rows: list[dict]) -> None:
  if not rows:
    return
  import csv
  keys = list(rows[0].keys())
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--json", default="")
  ap.add_argument("--out-dir", default="output")
  args = ap.parse_args()

  path = Path(args.json) if args.json else find_latest()
  results = json.loads(path.read_text())
  out = Path(args.out_dir)

  setup_rows = build_setup_rows(results)
  smc_tf_rows = build_smc_tf_rows(results)
  summary_rows = build_pair_summary(results)

  # Counts
  status_ct = Counter((r["style"], r["status"]) for r in setup_rows if r["style"] != "—")
  print(f"# Trading System Analysis — {path.name}")
  print(f"**Pairs:** {len(results)} · **Setups:** {len(setup_rows)} (50×5) · **TFs:** {', '.join(TFS)}\n")

  audit = Path("output/autodream/system_audit.json")
  if audit.exists():
    a = json.loads(audit.read_text())
    v = a.get("verdict", {})
    p = a.get("paper", {})
    print(f"**Audit:** {v.get('status')} — {v.get('shame_note')}")
    print(f"**Paper WR:** {p.get('all_win_rate', 0):.1%} all · {p.get('executable_win_rate', 0):.1%} executable")
    by_path = a.get("setups", {}).get("by_path", {})
    print(f"**OOS:** SMC {by_path.get('smc', {}).get('oos_avg', 0):.1%} · EW {by_path.get('ew', {}).get('oos_avg', 0):.1%}\n")

  print("## Status by style\n")
  print("| Style | Executable | Monitor | Not actionable |")
  print("| --- | ---: | ---: | ---: |")
  for style in STYLES:
    ex = status_ct.get((style, "executable"), 0)
    mon = status_ct.get((style, "monitor"), 0)
    na = status_ct.get((style, "not_actionable"), 0)
    print(f"| {style} | {ex} | {mon} | {na} |")

  print("\n## Pair summary (SMC + executive)\n")
  print_md_table(
    ["Symbol", "Pipeline", "Verdict", "Consensus", "Agree", "SMC Status", "Grade", "Conf", "Signal", "SMC TF", "Board"],
    summary_rows,
    ["symbol", "pipeline", "verdict", "consensus", "agree", "smc_status", "smc_grade", "smc_conf", "smc_signal", "smc_tf", "exec_action"],
  )

  exec_rows = [r for r in setup_rows if r["status"] == "executable"]
  print(f"\n## Executable setups ({len(exec_rows)})\n")
  print_md_table(
    ["Symbol", "Style", "TF", "Tier", "Dir", "Grade", "Conf", "Signal", "Score", "OOS", "Paper", "Confluence"],
    exec_rows,
    ["symbol", "style", "tf", "tier", "dir", "grade", "conf", "signal", "score", "oos", "paper", "confluence"],
  )

  smc_sig = [r for r in setup_rows if r["style"] == "smc" and r["signal"] == "Y"]
  print(f"\n## SMC entry signals ({len(smc_sig)})\n")
  print_md_table(
    ["Symbol", "TF", "Tier", "Dir", "Grade", "Conf", "Score", "OOS", "Confluence"],
    smc_sig,
    ["symbol", "tf", "tier", "dir", "grade", "conf", "score", "oos", "confluence"],
  )

  smc_mon = [r for r in setup_rows if r["style"] == "smc" and r["status"] == "monitor" and r["grade"] in ("A", "B")]
  print(f"\n## SMC monitor grade A/B ({len(smc_mon)}) — top 20\n")
  print_md_table(
    ["Symbol", "TF", "Dir", "Grade", "Conf", "Score", "Confluence"],
    sorted(smc_mon, key=lambda x: (-(x["score"] if isinstance(x["score"], int) else 0), str(x["symbol"])))[:20],
    ["symbol", "tf", "dir", "grade", "conf", "score", "confluence"],
  )

  print(f"\n## SMC confluence by timeframe (15m / 1h / 4h) — all pairs\n")
  print_md_table(
    ["Symbol", "TF", "Score", "Grade", "Conf", "Signal", "Probe", "VP", "Confluence tags"],
    smc_tf_rows,
    ["symbol", "tf", "score", "grade", "conf", "signal", "probe", "vp", "confluence"],
    max_rows=60,
  )

  print("\n## Full matrix: all pairs × all setup styles\n")
  print_md_table(
    ["Symbol", "Style", "TF", "Status", "Tier", "Dir", "Grade", "Conf", "Signal", "Score", "OOS", "Confluence"],
    sorted(setup_rows, key=lambda x: (x["symbol"], STYLES.index(x["style"]) if x["style"] in STYLES else 9)),
    ["symbol", "style", "tf", "status", "tier", "dir", "grade", "conf", "signal", "score", "oos", "confluence"],
    max_rows=80,
  )

  ts = path.stem.replace("top50_analysis_", "")
  save_csv(out / f"confluence_setups_{ts}.csv", setup_rows)
  save_csv(out / f"confluence_smc_tf_{ts}.csv", smc_tf_rows)
  save_csv(out / f"confluence_summary_{ts}.csv", summary_rows)
  print(f"\n---\n**CSV exports:**")
  print(f"- `output/confluence_setups_{ts}.csv` ({len(setup_rows)} rows)")
  print(f"- `output/confluence_smc_tf_{ts}.csv` ({len(smc_tf_rows)} rows)")
  print(f"- `output/confluence_summary_{ts}.csv` ({len(summary_rows)} rows)")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
