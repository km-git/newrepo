"""CLI: licensespend renewals upcoming --days 60"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from licensespend.cli_util import want_human
from licensespend.output import emit
from licensespend.renewals.service import to_ics, upcoming

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("upcoming")
def upcoming_cmd(
    ctx: typer.Context,
    days: int = typer.Option(60, "--days"),
    as_of: str | None = typer.Option(None, "--as-of"),
    ics: Path | None = typer.Option(None, "--ics", help="Optional ICS export path."),
    human: bool = typer.Option(False, "--human"),
) -> None:
    parsed = date.fromisoformat(as_of) if as_of else date(2026, 9, 7)
    report = upcoming(days=days, as_of=parsed)
    if ics:
        ics.write_text(to_ics(report), encoding="utf-8")
    typer.echo(emit(report.model_dump(mode="json"), human=want_human(ctx, human)), nl=False)
