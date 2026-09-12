"""CLI: licensespend shadow scan"""

from __future__ import annotations

from pathlib import Path

import typer

from licensespend.cli_util import FIXTURE_ANY, want_human
from licensespend.constants import EXAMPLES
from licensespend.output import emit
from licensespend.shadow.service import scan

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("scan")
def scan_cmd(
    ctx: typer.Context,
    fixture: Path | None = FIXTURE_ANY,
    human: bool = typer.Option(False, "--human"),
) -> None:
    report = scan(fixture or (EXAMPLES / "shadow"))
    typer.echo(emit(report.model_dump(mode="json"), human=want_human(ctx, human)), nl=False)
