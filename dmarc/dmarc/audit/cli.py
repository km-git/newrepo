"""Audit CLI."""

from __future__ import annotations

import json

import typer

from dmarc.audit.service import build_inventory

app = typer.Typer(help="Workspace audit and OSS inventory")


@app.command("inventory")
def inventory_cmd() -> None:
    """Build dmarc-inventory.json and ensure DB schema exists."""
    result = build_inventory()
    typer.echo(json.dumps({"status": "ok", "tools": len(result["tools"]), "path": "dmarc-inventory.json"}))
