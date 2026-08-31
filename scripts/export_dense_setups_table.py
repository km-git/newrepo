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
    font-family: "SF Mono", "Cascadia Mono", "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
    font-size: var(--fs);
    font-variant-numeric: tabular-nums;
  }}
  body {{ margin: 0; padding: 8px; background: #0b0f14; color: #dbe4ee; }}
  h1 {{ font-size: calc(var(--fs) + 5px); margin: 0 0 4px; }}
  .meta {{ color: #7d8b99; margin-bottom: 8px; }}
  .wrap {{ overflow: auto; max-height: 95vh; border: 1px solid #1e2a36; }}
  table {{ border-collapse: collapse; width: max-content; min-width: 100%; }}
  th {{ position: sticky; top: 0; background: #15202b; color: #8ab4f8; padding: 4px 6px; border: 1px solid #243447; white-space: nowrap; z-index: 2; }}
  td {{ padding: 3px 5px; border: 1px solid #1a2530; white-space: nowrap; max-width: 280px; overflow: hidden; text-overflow: ellipsis; }}
  tr.even td {{ background: #0f1419; }}
  tr.odd td {{ background: #0b1015; }}
  tr.executable td {{ border-left: 2px solid #2ecc71; }}
  tr.sqs-execute td:first-child {{ color: #2ecc71; font-weight: 700; }}
  tr.sqs-standby td:first-child {{ color: #f1c40f; }}
  #filter {{ margin-bottom: 8px; padding: 6px 8px; width: 320px; background: #15202b; border: 1px solid #243447; color: #dbe4ee; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="meta">{len(rows)} rows × {len(cols)} columns · {ts}</p>
<input id="filter" type="search" placeholder="Filter symbol / TF / tier…" oninput="filterRows(this.value)"/>
<div class="wrap">
<table id="grid">
<thead><tr>{head_cells}</tr></thead>
<tbody>
{"".join(body_rows)}
</tbody>
</table>
</div>
<script>
function filterRows(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('#grid tbody tr').forEach(tr => {{
    tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""
  out_path.parent.mkdir(parents=True, exist_ok=True)
  out_path.write_text(doc, encoding="utf-8")


def main() -> int:
  ap = argparse.ArgumentParser(description="Dense pair×TF setups export")
  ap.add_argument("--input", type=Path, default=ROOT / "output" / "latest_limit_orders_all_tf.csv")
  ap.add_argument("--csv-out", type=Path, default=ROOT / "reports" / "all_pair_tf_setups_dense.csv")
  ap.add_argument("--html-out", type=Path, default=ROOT / "reports" / "all_pair_tf_setups_dense.html")
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
  ap.add_argument("--title", default="All Pair × TF Setups — Dense View")
  args = ap.parse_args()

  if not args.input.exists():
    print(f"Missing input: {args.input}", file=sys.stderr)
    return 1

  cols, rows = load_rows(args.input)
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

  write_dense_html(cols, rows, args.html_out, title=args.title)
  print(f"Wrote {len(rows)} rows × {len(cols)} cols")
  print(f"  CSV:  {args.csv_out}")
  print(f"  HTML: {args.html_out}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
