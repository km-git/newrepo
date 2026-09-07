"""Access CLI."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.access.service import map_access

app = typer.Typer(help="IAM access governance")


@app.command("map")
def map_cmd(
    store: str = typer.Option("42", "--store", help="findings_stores.id=N"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Map principals that can reach a data store."""
    store_id = int(store.split("=")[-1]) if "=" in store else int(store)
    emit(map_access(store_id), human=human, title="Access Map")
