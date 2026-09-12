"""Exposure CLI."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.exposure.service import scan_exposure

app = typer.Typer(help="Public exposure detection")


@app.command("scan")
def scan_cmd(
    provider: str = typer.Option("aws", "--provider", "-p"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Scan for public buckets, unencrypted DBs, etc."""
    emit(scan_exposure(provider=provider), human=human, title="Exposure Findings")
