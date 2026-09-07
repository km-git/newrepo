"""Aggregate report CLI."""

from __future__ import annotations

import typer

from dmarc.aggregate_report.service import generate_aggregate_report

app = typer.Typer(help="DMARC aggregate HTML reports")


@app.command("report")
def report_cmd(since: str = typer.Option("30d", "--since")) -> None:
    """Generate reports/aggregate_YYYY-MM.html with Plotly charts."""
    path = generate_aggregate_report(since)
    typer.echo(f"Wrote {path}")
