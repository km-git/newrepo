"""CLI helpers shared by module Typer apps."""

from __future__ import annotations

from pathlib import Path

import typer


def want_human(ctx: typer.Context, local: bool = False) -> bool:
    parent = False
    if ctx.parent and ctx.parent.obj:
        parent = bool(ctx.parent.obj.get("human"))
    return bool(local or parent)


FIXTURE_DIR = typer.Option(None, "--fixture", exists=True, file_okay=False, dir_okay=True)
FIXTURE_ANY = typer.Option(None, "--fixture")
OUT_DIR = typer.Option(Path("reports"), "--out")
