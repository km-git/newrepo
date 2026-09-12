"""Risk CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dspm._output import emit
from dspm.classification.service import classify_csv
from dspm.risk.service import risks_to_dict, score_findings

app = typer.Typer(help="DuckDB risk scoring")


@app.command("score")
def score_cmd(
    data: Path = typer.Option(Path("examples/sample.csv"), "--data"),
    since: str = typer.Option("7d", "--since"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Score classified findings by risk (0-100)."""
    findings = classify_csv(data)
    exposures = [{"type": "public_s3", "resource": "s3://public-bucket"}] if findings else []
    scores = score_findings(findings, exposures=exposures)
    emit(risks_to_dict(scores), human=human, title=f"Risk Scores (since {since})")
