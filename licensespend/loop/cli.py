"""CLI: licensespend loop watch|classify|monthly"""

from __future__ import annotations

import typer

from licensespend.cli_util import want_human
from licensespend.loop.service import classify_finding, monthly, watch
from licensespend.output import emit

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("watch")
def watch_cmd(ctx: typer.Context, human: bool = typer.Option(False, "--human")) -> None:
    typer.echo(emit(watch(), human=want_human(ctx, human)), nl=False)


@app.command("classify")
def classify_cmd(
    ctx: typer.Context,
    sku: str = typer.Option(..., "--sku"),
    idle_days: int = typer.Option(..., "--idle-days"),
    user_id_hash: str = typer.Option(..., "--user-id-hash"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    result = classify_finding(sku=sku, idle_days=idle_days, user_id_hash=user_id_hash)
    typer.echo(emit(result.model_dump(mode="json"), human=want_human(ctx, human)), nl=False)


@app.command("monthly")
def monthly_cmd(ctx: typer.Context, human: bool = typer.Option(False, "--human")) -> None:
    typer.echo(emit(monthly().model_dump(mode="json"), human=want_human(ctx, human)), nl=False)
