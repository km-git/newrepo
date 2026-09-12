"""Classification CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dspm._output import emit
from dspm.classification.service import classify_csv, findings_to_dict

app = typer.Typer(help="PII/PHI/PCI classification")


@app.command("run")
def classify_run(
    path: Path = typer.Argument(..., help="CSV file to classify"),
    human: bool = typer.Option(False, "--human"),
    max_rows: int = typer.Option(100, "--max-rows"),
) -> None:
    """Classify a CSV file for sensitive data."""
    findings = classify_csv(path, max_rows=max_rows)
    emit(findings_to_dict(findings), human=human, title="Classified Findings")
