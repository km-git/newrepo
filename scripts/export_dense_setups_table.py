#!/usr/bin/env python3
"""Export pair×TF trade setups as dense scrollable HTML + CSV (every column)."""

from __future__ import annotations

import argparse
import csv
import html
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

TF_ORDER = ["1w", "1d", "12h", "4h", "1h", "15m"]


def _tf_key(tf: str) -> int:
  try:
    return TF_ORDER.index(tf)
  except ValueError:
    return 99


def load_rows(csv_path: Path, *, primary_only: bool = True) -> tuple[list[str], list[dict]]:
  with csv_path.open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
  if primary_only:
    rows = [r for r in rows if r.get("row_type", "primary") == "primary"]
  if not rows:
    return [], []
  cols = list(rows[0].keys())
  rows.sort(key=lambda r: (
    -float(r.get("sqs_score") or 0),
    r.get("symbol", ""),
    _tf_key(r.get("timeframe", "")),
  ))
  return cols, rows


def write_dense_html(
  cols: list[str],
  rows: list[dict],
  out_path: Path,
  *,
  title: str,
  font_size_px: int = 9,
) -> None:
  ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
  head_cells = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
  body_rows: list[str] = []
  for i, row in enumerate(rows):
    cls = "even" if i % 2 == 0 else "odd"
    tier = row.get("gtc_tier", "")
    sqs = str(row.get("sqs_tier") or "")
    if tier == "executable":
      cls += " executable"
    if sqs == "EXECUTE":
      cls += " sqs-execute"
    elif sqs == "STANDBY":
      cls += " sqs-standby"
    cells = "".join(
      f"<td title='{html.escape(c)}: {html.escape(str(row.get(c) or ''))}'>{html.escape(str(row.get(c) or ''))}</td>"
      for c in cols
    )
    body_rows.append(f"<tr class='{cls}'>{cells}</tr>")

  doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>
  :root {{
    --fs: {font_size_px}px;
    --lh: 1.25;
    font-family: "SF Mono", "Cascadia Mono", "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
    font-size: var(--fs);
    line-height: var(--lh);
    font-variant-numeric: tabular-nums;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
    font-feature-settings: "tnum" 1, "zero" 1;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 8px 10px; background: #0b0f14; color: #dbe4ee; }}
  h1 {{ font-size: calc(var(--fs) + 5px); font-weight: 700; margin: 0 0 2px; letter-spacing: -0.02em; }}
  .meta {{ color: #7d8b99; margin-bottom: 8px; font-size: calc(var(--fs) + 1px); }}
  .toolbar {{ display: flex; gap: 8px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }}
  .toolbar label {{ color: #9aa7b5; font-size: calc(var(--fs) + 1px); }}
  .toolbar input {{ width: 220px; padding: 4px 6px; font: inherit; background: #121820; color: #e6edf3; border: 1px solid #2a3440; border-radius: 4px; }}
  .wrap {{ overflow: auto; max-height: calc(100vh - 72px); border: 1px solid #243040; border-radius: 4px; }}
  table {{ border-collapse: collapse; min-width: max-content; width: 100%; }}
  th, td {{
    border: 1px solid #1c2632;
    padding: 1px 4px;
    white-space: nowrap;
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    vertical-align: top;
  }}
  th {{
    position: sticky;
    top: 0;
    background: #121820;
    z-index: 2;
    font-weight: 700;
    color: #9fd0ff;
    letter-spacing: 0.01em;
    text-transform: lowercase;
    font-size: calc(var(--fs) - 1px);
  }}
  td:first-child, th:first-child {{
    position: sticky;
    left: 0;
    background: #10161d;
    z-index: 1;
    font-weight: 600;
  }}
  th:first-child {{ z-index: 3; background: #121820; }}
  tr.even td {{ background: #0b0f14; }}
  tr.odd td {{ background: #090d12; }}
  tr.executable td {{ background: #0d1a12; }}
  tr.executable td:first-child {{ background: #0d1a12; }}
  tr.sqs-execute td:first-child {{ color: #2ecc71; font-weight: 700; }}
  tr.sqs-standby td:first-child {{ color: #f1c40f; }}
  tr:hover td {{ background: #172231 !important; }}
  tr.hidden {{ display: none; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="meta">{ts} · {len(rows)} rows · {len(cols)} columns · all pairs × all timeframes</p>
<div class="toolbar">
  <label>Filter <input id="q" type="search" placeholder="symbol, tf, direction, tier…" autofocus/></label>
</div>
<div class="wrap">
<table id="setups">
<thead><tr>{head_cells}</tr></thead>
<tbody>
{"".join(body_rows)}
</tbody>
</table>
</div>
<script>
const q = document.getElementById('q');
const rows = [...document.querySelectorAll('#setups tbody tr')];
q.addEventListener('input', () => {{
  const needle = q.value.trim().toLowerCase();
  rows.forEach(r => {{
    r.classList.toggle('hidden', needle && !r.textContent.toLowerCase().includes(needle));
  }});
}});
</script>
</body>
</html>"""
  out_path.parent.mkdir(parents=True, exist_ok=True)
  out_path.write_text(doc, encoding="utf-8")


def main() -> int:
  ap = argparse.ArgumentParser(description="Dense pair×TF setups export")
  ap.add_argument("--input", type=Path, default=ROOT / "output" / "latest_limit_orders_all_tf.csv")
  ap.add_argument("--csv", type=Path, default=None, help="Alias for --input")
  ap.add_argument("--csv-out", type=Path, default=ROOT / "reports" / "all_pair_tf_setups_dense.csv")
  ap.add_argument("--html-out", type=Path, default=ROOT / "reports" / "all_pair_tf_setups_dense.html")
  ap.add_argument("--html", type=Path, default=None, help="Alias for --html-out")
  ap.add_argument(
    "--high-accuracy-only",
    action="store_true",
    help="Keep only geometry-valid, pair-validated setups (pair×TF n>=5, EXECUTE)",
  )
  ap.add_argument(
    "--candidate-only",
    action="store_true",
    help="Keep technically valid executable/monitor candidates; makes no accuracy claim",
  )
  ap.add_argument("--min-sqs", type=float, default=None, help="Minimum sqs_score")
  ap.add_argument(
    "--include-rejected",
    action="store_true",
    help="Include geometry-invalid rows in the main table (off by default)",
  )
  ap.add_argument(
    "--include-contingent",
    action="store_true",
    help="Include contingent (non-primary) rows",
  )
  ap.add_argument(
    "--rejected-out",
    type=Path,
    default=ROOT / "reports" / "rejected_setups_geometry.csv",
    help="Diagnostic CSV for rejected geometry",
  )
  ap.add_argument("--font-size", type=int, default=9, help="Base font size in px (default: 9)")
  ap.add_argument("--title", default="All Pair × TF Setups — Dense View")
  args = ap.parse_args()

  src = args.csv or args.input
  html_out = args.html or args.html_out
  if not src.exists():
    print(f"Missing input: {src}", file=sys.stderr)
    return 1

  cols, rows = load_rows(src, primary_only=not args.include_contingent)
  rejected = [r for r in rows if str(r.get("geometry_valid") or "Y") != "Y"]
  if not args.include_rejected:
    rows = [r for r in rows if str(r.get("geometry_valid") or "Y") == "Y"]
  if args.high_accuracy_only:
    rows = [
      r for r in rows
      if str(r.get("geometry_valid") or "") == "Y"
      and str(r.get("sqs_tier") or "") == "EXECUTE"
      and str(r.get("hist_scope") or "") == "pair_tf"
      and int(float(r.get("hist_n") or 0)) >= 5
      and str(r.get("gtc_tier") or "") == "executable"
      and not str(r.get("sqs_action") or "").startswith("WATCH")
    ]
    args.title += " (Pair-Validated)"
  if args.candidate_only:
    rows = [
      r for r in rows
      if str(r.get("geometry_valid") or "") == "Y"
      and str(r.get("sqs_tier") or "") in ("EXECUTE", "STANDBY")
      and str(r.get("gtc_tier") or "") in ("executable", "monitor")
      and not str(r.get("sqs_action") or "").startswith("WATCH")
    ]
    args.title += " (Technical Candidates; Unvalidated)"
  if args.min_sqs is not None:
    rows = [r for r in rows if float(r.get("sqs_score") or 0) >= args.min_sqs]

  args.csv_out.parent.mkdir(parents=True, exist_ok=True)
  with args.csv_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

  args.rejected_out.parent.mkdir(parents=True, exist_ok=True)
  with args.rejected_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rejected)

  write_dense_html(
    cols,
    rows,
    html_out,
    title=args.title,
    font_size_px=max(7, min(14, args.font_size)),
  )
  print(f"Wrote {len(rows)} rows × {len(cols)} cols")
  print(f"  CSV:  {args.csv_out}")
  print(f"  HTML: {html_out}")
  print(f"  Rejected geometry: {len(rejected)} → {args.rejected_out}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
