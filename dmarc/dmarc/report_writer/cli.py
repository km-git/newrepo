"""Report writer CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dmarc.report_writer.service import generate_report

app = typer.Typer(help="Deliverability report generation")


@app.command("generate")
def generate_cmd(
    domain: str = typer.Option(..., "--domain"),
    since: str = typer.Option("30d", "--since"),
    output: Path | None = typer.Option(None, "--output"),
) -> None:
    """Write report.md + report.json with liability disclaimer."""
    md, js = generate_report(domain, since, output)
    typer.echo(f"Wrote {md} and {js}")
