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
  font_size_px: int = 9,
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


def main() -> None:
  p = argparse.ArgumentParser(description="Dense HTML table — all pair×TF setups, all columns")
  p.add_argument("--csv", default="output/latest_limit_orders_all_tf.csv")
  p.add_argument("--html", default="reports/all_pair_tf_setups_dense.html")
  p.add_argument("--csv-out", default="reports/all_pair_tf_setups_dense.csv")
  p.add_argument("--include-contingent", action="store_true")
  p.add_argument("--font-size", type=int, default=9, help="Base font size in px (default: 9)")
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
    font_size_px=max(7, min(14, args.font_size)),
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
