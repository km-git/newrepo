"""Encryption check CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dspm._output import emit
from dspm.encryption_check.service import check_encryption

app = typer.Typer(help="At-rest + in-flight encryption checks")


@app.command()
def check(
    path: Path = typer.Argument(Path("terraform"), help="IaC directory"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Scan IaC for encryption misconfigurations (Trivy v0.70+)."""
    emit(check_encryption(path), human=human, title="Encryption Status")
