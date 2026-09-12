"""Audit CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dspm._output import emit
from dspm.audit.service import ensure_schema, write_inventory_json

app = typer.Typer(help="Workspace and OSS tool inventory")


@app.command("inventory")
def inventory(
    human: bool = typer.Option(False, "--human", help="Pretty-print table"),
    out: Path = typer.Option(Path("dspm-inventory.json"), "--out", help="JSON output path"),
) -> None:
    """List all 12 modules and 8 primary OSS tools."""
    ensure_schema()
    data = write_inventory_json(out)
    emit(data, human=human, title="DSPM Inventory")
