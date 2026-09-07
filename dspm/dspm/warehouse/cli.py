"""Warehouse CLI."""

from __future__ import annotations

import typer

from dspm._output import emit
from dspm.warehouse.service import execute_sql, query_history

app = typer.Typer(help="DuckDB SQL workspace (Databricks/Snowflake inspired)")


@app.command("query")
def query_cmd(
    sql: str = typer.Argument(..., help="SQL query"),
    user: str = typer.Option("analyst", "--user"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    emit(execute_sql(sql, user=user), human=human, title="Query Result")


@app.command("history")
def history_cmd(human: bool = typer.Option(False, "--human")) -> None:
    emit(query_history(), human=human, title="Query History")
