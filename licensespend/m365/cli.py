"""CLI: licensespend m365 seats --fixture examples/m365/"""

from __future__ import annotations

from pathlib import Path

import typer

from licensespend.cli_util import FIXTURE_DIR, want_human
from licensespend.constants import EXAMPLES, include_email
from licensespend.m365.service import load_fixture
from licensespend.output import emit

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("seats")
def seats_cmd(
    ctx: typer.Context,
    fixture: Path | None = FIXTURE_DIR,
    human: bool = typer.Option(False, "--human"),
) -> None:
    report = load_fixture(fixture or (EXAMPLES / "m365"))
    payload = report.model_dump(mode="json")
    if not include_email():
        for seat in payload["seats"]:
            seat["email"] = None
    typer.echo(emit(payload, human=want_human(ctx, human)), nl=False)
