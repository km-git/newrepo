"""CLI: licensespend audit inventory."""

from __future__ import annotations

import typer

from licensespend.audit.service import inventory
from licensespend.cli_util import want_human
from licensespend.output import emit

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("inventory")
def inventory_cmd(
    ctx: typer.Context,
    human: bool = typer.Option(False, "--human"),
) -> None:
    typer.echo(emit(inventory().model_dump(mode="json"), human=want_human(ctx, human)), nl=False)
