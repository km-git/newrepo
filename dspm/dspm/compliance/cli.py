"""Compliance CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dspm._output import emit
from dspm.compliance.service import map_compliance

app = typer.Typer(help="GDPR/HIPAA/PCI/SOC2 control mapping")


@app.command("map")
def map_cmd(
    framework: str = typer.Option("gdpr", "--framework", "-f"),
    data: Path = typer.Option(Path("examples/sample.csv"), "--data"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Map findings to compliance controls."""
    emit(map_compliance(framework, data), human=human, title=f"Compliance ({framework})")
