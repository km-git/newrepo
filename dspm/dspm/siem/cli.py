"""SIEM CLI."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.siem.service import correlate_findings, ingest_event, search_events

app = typer.Typer(help="SIEM event search and correlation (Splunk inspired)")


@app.command("search")
def search_cmd(
    query: str = typer.Argument("*", help="Search query (regex)"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    emit(search_events(query), human=human, title="SIEM Events")


@app.command("ingest")
def ingest_cmd(
    event_type: str = typer.Option("finding", "--type"),
    severity: str = typer.Option("medium", "--severity"),
    source: str = typer.Option("dspm", "--source"),
    message: str = typer.Argument(...),
    human: bool = typer.Option(False, "--human"),
) -> None:
    emit(ingest_event(event_type, severity, source, message), human=human)


@app.command("correlate")
def correlate_cmd(human: bool = typer.Option(False, "--human")) -> None:
    from pathlib import Path

    from dspm.classification.service import classify_csv, findings_to_dict
    from dspm.exposure.service import scan_exposure

    findings = findings_to_dict(classify_csv(Path("examples/sample.csv"), max_rows=20))
    exposures = scan_exposure(provider="aws")
    emit(correlate_findings(findings, exposures), human=human, title="Correlated Alerts")
