"""Observability CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dspm._output import emit
from dspm.classification.service import classify_csv, findings_to_dict
from dspm.exposure.service import scan_exposure
from dspm.observability.service import dashboard_summary, evaluate_alerts, record_metric, seed_alert_rules
from dspm.risk.service import risks_to_dict, score_findings

app = typer.Typer(help="Metrics and alerting (Datadog inspired)")


@app.command("dashboard")
def dashboard_cmd(human: bool = typer.Option(False, "--human")) -> None:
    root = Path("examples/sample.csv")
    findings = findings_to_dict(classify_csv(root, max_rows=30))
    exposures = scan_exposure(provider="aws")
    exposure_rows = [e.model_dump() if hasattr(e, "model_dump") else e for e in exposures]
    risks = risks_to_dict(score_findings(findings[:10], exposures=exposure_rows))
    summary = dashboard_summary(findings, risks, exposures)
    alerts = evaluate_alerts(summary)
    emit({"summary": summary, "alerts": alerts}, human=human, title="Observability Dashboard")


@app.command("metric")
def metric_cmd(
    name: str = typer.Argument(...),
    value: float = typer.Argument(...),
    human: bool = typer.Option(False, "--human"),
) -> None:
    emit(record_metric(name, value), human=human)


@app.command("alerts")
def alerts_cmd(human: bool = typer.Option(False, "--human")) -> None:
    emit(seed_alert_rules(), human=human, title="Alert Rules")
