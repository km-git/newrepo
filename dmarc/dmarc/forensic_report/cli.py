"""Forensic report CLI."""

from __future__ import annotations

import typer

from dmarc.forensic_report.service import ingest_forensic_sample, list_forensic

app = typer.Typer(help="DMARC forensic (RUF) reports")


@app.command("list")
def list_cmd(
    domain: str = typer.Option("example.com.au", "--domain"),
    since: str = typer.Option("30d", "--since"),
    demo: bool = typer.Option(False, "--demo"),
) -> None:
    """List scrubbed forensic findings (often empty — RUF is rarely sent)."""
    if demo:
        findings = ingest_forensic_sample(domain)
    else:
        findings = list_forensic(domain, since)
    typer.echo(f"Forensic rows: {len(findings)}")
