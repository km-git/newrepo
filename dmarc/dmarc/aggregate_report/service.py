"""Aggregate HTML report generator (DuckDB + Plotly)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb
import plotly.graph_objects as go

from dmarc.config import DB_PATH, REPORTS_DIR
from dmarc.db import fetch_all, init_db


def _since_filter(since: str) -> str:
    mapping = {"7d": 7, "30d": 30, "90d": 90}
    days = mapping.get(since, 30)
    return f"received_at >= current_timestamp - interval '{days} days'"


def generate_aggregate_report(since: str = "30d") -> Path:
    init_db()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    out = REPORTS_DIR / f"aggregate_{month}.html"

    rows = fetch_all("findings_dmarc", limit=5000)
    if not rows:
        out.write_text(
            "<html><body><h1>Email Deliverability & Brand-Protection Review</h1>"
            "<p>No aggregate DMARC rows yet. Run <code>dmarc ingest pull --demo</code>.</p></body></html>",
            encoding="utf-8",
        )
        return out

    conn = duckdb.connect(str(DB_PATH))
    conn.execute("CREATE OR REPLACE VIEW v_dmarc AS SELECT * FROM findings_dmarc")
    summary = conn.execute(
        """
        SELECT source_org, SUM(count) AS total,
               SUM(CASE WHEN dkim_result='pass' AND spf_result='pass' THEN count ELSE 0 END) AS pass_count
        FROM v_dmarc GROUP BY 1 ORDER BY total DESC LIMIT 20
        """
    ).fetchall()
    conn.close()

    orgs = [r[0] for r in summary]
    totals = [r[1] for r in summary]
    passes = [r[2] for r in summary]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Total", x=orgs, y=totals))
    fig.add_trace(go.Bar(name="Pass (DKIM+SPF)", x=orgs, y=passes))
    fig.update_layout(
        title="DMARC aggregate pass/fail by source organisation",
        barmode="group",
        template="plotly_dark",
    )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Aggregate {month}</title></head>
<body>
<h1>Email Deliverability &amp; Brand-Protection Review — Aggregate</h1>
<p>Period: last {since}. Rows: {len(rows)}.</p>
{fig.to_html(full_html=False, include_plotlyjs="cdn")}
</body></html>"""
    out.write_text(html, encoding="utf-8")
    return out
