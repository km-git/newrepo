"""Catalog CLI."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.catalog.service import build_lineage_graph, register_asset, sync_from_discovery
from dspm.discovery.service import discover_directory
from dspm.store.db import fetch_all

app = typer.Typer(help="Data catalog and lineage (Unity Catalog / OpenMetadata inspired)")


@app.command("register")
def register_cmd(
    name: str = typer.Argument(...),
    asset_type: str = typer.Option("table", "--type"),
    owner: str = typer.Option("data-team", "--owner"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    emit(register_asset(name, asset_type, owner), human=human)


@app.command("lineage")
def lineage_cmd(human: bool = typer.Option(False, "--human")) -> None:
    emit(build_lineage_graph(), human=human, title="Lineage Graph")


@app.command("list")
def list_cmd(human: bool = typer.Option(False, "--human")) -> None:
    emit(fetch_all("catalog_assets"), human=human, title="Catalog Assets")


@app.command("sync")
def sync_cmd(
    path: str = typer.Option("examples", "--path"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from pathlib import Path

    stores = [s.model_dump() for s in discover_directory(Path(path))]
    emit(sync_from_discovery(stores), human=human)
