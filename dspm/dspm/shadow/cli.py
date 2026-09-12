"""Shadow data CLI."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.shadow.service import scan_shadow

app = typer.Typer(help="Shadow / forgotten data detection")


@app.command("scan")
def scan_cmd(human: bool = typer.Option(False, "--human")) -> None:
    """Heuristic scan for shadow data stores."""
    emit(scan_shadow(), human=human, title="Shadow Data")
