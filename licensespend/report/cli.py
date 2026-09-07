"""CLI: licensespend report build --client acme --out reports/"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from licensespend.cli_util import FIXTURE_ANY, OUT_DIR, want_human
from licensespend.constants import EXAMPLES
from licensespend.output import emit
from licensespend.report.service import build

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("build")
def build_cmd(
    ctx: typer.Context,
    client: str = typer.Option("fixture", "--client"),
    out: Path = OUT_DIR,
    fixture: Path | None = FIXTURE_ANY,
    as_of: str | None = typer.Option(None, "--as-of"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    files = build(
        client=client,
        out_dir=out,
        fixture_root=fixture or EXAMPLES,
        as_of=date.fromisoformat(as_of) if as_of else date(2026, 9, 7),
    )
    typer.echo(emit(files.model_dump(mode="json"), human=want_human(ctx, human)), nl=False)
