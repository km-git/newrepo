"""Remediation CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dspm._output import emit
from dspm.remediation.service import build_plan, list_policies, write_plan

app = typer.Typer(help="Cloud Custodian remediation")


@app.command("plan")
def plan_cmd(
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Dry-run mode"),
    out: Path = typer.Option(Path("remediation_plan.json"), "--out"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Generate remediation plan."""
    data = write_plan(out, dry_run=dry_run)
    emit(data, human=human, title="Remediation Plan")


@app.command("apply")
def apply_cmd(
    policy: str = typer.Option(..., "--policy"),
    limit: int = typer.Option(5, "--limit"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Apply a remediation policy (dry-run unless --no-dry-run)."""
    emit(
        {"policy": policy, "limit": limit, "status": "dry-run-only", "policies": list_policies()},
        human=human,
    )
