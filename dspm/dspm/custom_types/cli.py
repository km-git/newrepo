"""Custom types CLI."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.classification.recognizers import check_custom_type
from dspm.custom_types.service import list_types

app = typer.Typer(help="Custom data type registry")


@app.command("list")
def list_cmd(human: bool = typer.Option(False, "--human")) -> None:
    """List registered custom data types."""
    emit(list_types(), human=human, title="Custom Types")


@app.command("test")
def test_cmd(
    type_name: str = typer.Option(..., "--type"),
    text: str = typer.Option(..., "--text"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    """Test a custom type against sample text."""
    emit(check_custom_type(type_name, text), human=human)
