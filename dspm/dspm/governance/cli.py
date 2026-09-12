"""Governance CLI."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.governance.service import apply_mask, list_policies, seed_policies

app = typer.Typer(help="Masking + row access policies (Snowflake Horizon inspired)")


@app.command("policies")
def policies_cmd(human: bool = typer.Option(False, "--human")) -> None:
    emit(list_policies(), human=human, title="Governance Policies")


@app.command("mask")
def mask_cmd(
    value: str = typer.Argument(...),
    data_type: str = typer.Option("PII", "--type"),
    role: str = typer.Option("DATA_USER", "--role"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    emit({"original": value, "masked": apply_mask(value, data_type, role)}, human=human)


@app.command("seed")
def seed_cmd(human: bool = typer.Option(False, "--human")) -> None:
    emit(seed_policies(), human=human)
