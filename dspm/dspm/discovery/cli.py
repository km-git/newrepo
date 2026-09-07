"""Discovery CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from dspm._output import emit
from dspm.discovery.service import discover_cloud, discover_directory, stores_to_dict

app = typer.Typer(help="Agentless data-store inventory")


@app.command("dir")
def dir_cmd(
    path: Path = typer.Argument(..., help="Directory to scan"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Scan a local directory for data stores."""
    stores = discover_directory(path)
    emit(stores_to_dict(stores), human=human, title="Discovered Stores")


@app.command("cloud")
def cloud_cmd(
    provider: str = typer.Option("aws", "--provider", "-p"),
    profile: str | None = typer.Option(None, "--profile"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Enumerate cloud data stores via CloudQuery (or fixture)."""
    stores = discover_cloud(provider, profile)
    emit(stores_to_dict(stores), human=human, title=f"Cloud Stores ({provider})")
