#!/usr/bin/env python3
"""Export all pair×TF trade setups as a dense scrollable HTML table (every column)."""

from __future__ import annotations

import argparse
import csv
import html
from datetime import datetime, timezone
from pathlib import Path

TF_ORDER = ["1w", "1d", "4h", "1h", "15m", "12h", "1h", "4h"]


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
  rows.sort(key=lambda r: (r.get("symbol", ""), _tf_key(r.get("timeframe", "")), r.get("style", "")))
  return cols, rows


def write_dense_html(
  cols: list[str],
  rows: list[dict],
  out_path: Path,
  *,
  title: str,
) -> None:
  ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
  head_cells = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
  body_rows: list[str] = []
  for i, row in enumerate(rows):
    cls = "even" if i % 2 == 0 else "odd"
    tier = row.get("gtc_tier", "")
    if tier == "executable":
      cls += " executable"
    cells = "".join(
      f"<td title='{html.escape(c)}'>{html.escape(str(row.get(c) or ''))}</td>"
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
  :root {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11px; }}
  body {{ margin: 0; padding: 12px; background: #0d1117; color: #e6edf3; }}
  h1 {{ font-size: 16px; margin: 0 0 4px; }}
  .meta {{ color: #8b949e; margin-bottom: 12px; }}
  .wrap {{ overflow: auto; max-height: calc(100vh - 80px); border: 1px solid #30363d; border-radius: 6px; }}
  table {{ border-collapse: collapse; min-width: max-content; }}
  th, td {{ border: 1px solid #30363d; padding: 3px 6px; white-space: nowrap; max-width: 280px; overflow: hidden; text-overflow: ellipsis; }}
  th {{ position: sticky; top: 0; background: #161b22; z-index: 2; font-weight: 600; }}
  td:first-child, th:first-child {{ position: sticky; left: 0; background: #161b22; z-index: 1; }}
  th:first-child {{ z-index: 3; }}
  tr.even td {{ background: #0d1117; }}
  tr.odd td {{ background: #010409; }}
  tr.executable td {{ background: #0f2419; }}
  tr.executable td:first-child {{ background: #0f2419; }}
  tr:hover td {{ background: #1f2a37 !important; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="meta">{ts} · {len(rows)} rows · {len(cols)} columns · source dense export</p>
<div class="wrap">
<table>
<thead><tr>{head_cells}</tr></thead>
<tbody>
{"".join(body_rows)}
</tbody>
</table>
</div>
</body>
</html>"""
  out_path.parent.mkdir(parents=True, exist_ok=True)
  out_path.write_text(doc, encoding="utf-8")


def main() -> None:
  p = argparse.ArgumentParser(description="Dense HTML table — all pair×TF setups, all columns")
  p.add_argument("--csv", default="output/latest_limit_orders_all_tf.csv")
  p.add_argument("--html", default="reports/all_pair_tf_setups_dense.html")
  p.add_argument("--csv-out", default="reports/all_pair_tf_setups_dense.csv")
  p.add_argument("--include-contingent", action="store_true")
  args = p.parse_args()

  src = Path(args.csv)
  cols, rows = load_rows(src, primary_only=not args.include_contingent)
  if not rows:
    raise SystemExit(f"No rows in {src}")

  write_dense_html(
    cols,
    rows,
    Path(args.html),
    title="All Trade Setups — Every Pair × Timeframe (all columns)",
  )

  out_csv = Path(args.csv_out)
  out_csv.parent.mkdir(parents=True, exist_ok=True)
  with out_csv.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

  print({
    "source": str(src.resolve()),
    "rows": len(rows),
    "columns": len(cols),
    "html": str(Path(args.html).resolve()),
    "csv": str(out_csv.resolve()),
  })


if __name__ == "__main__":
  main()
