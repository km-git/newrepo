"""CLI: licensespend usage unused --idle-days 90 --fixture examples/"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from licensespend.cli_util import FIXTURE_ANY, want_human
from licensespend.constants import EXAMPLES
from licensespend.output import emit
from licensespend.usage.service import unused_seats

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("unused")
def unused_cmd(
    ctx: typer.Context,
    idle_days: int = typer.Option(90, "--idle-days"),
    fixture: Path | None = FIXTURE_ANY,
    as_of: str | None = typer.Option(None, "--as-of", help="YYYY-MM-DD (tests pin this)."),
    human: bool = typer.Option(False, "--human"),
) -> None:
    parsed_as_of = date.fromisoformat(as_of) if as_of else date(2026, 9, 7)
    report = unused_seats(
        fixture_root=fixture or EXAMPLES,
        idle_days=idle_days,
        as_of=parsed_as_of,
    )
    typer.echo(emit(report.model_dump(mode="json"), human=want_human(ctx, human)), nl=False)
