"""SPF parser CLI."""

from __future__ import annotations

import json

import typer

from dmarc.spf_parser.service import parse_spf

app = typer.Typer(help="SPF record parser")


@app.command("parse")
def parse_cmd(domain: str = typer.Option(..., "--domain")) -> None:
    """Parse SPF and warn on lookup limits."""
    finding = parse_spf(domain)
    typer.echo(json.dumps(finding.model_dump(mode="json"), indent=2))
