"""licensespend CLI. JSON by default; pass --human for a table."""

from __future__ import annotations

from typing import Any

import typer

from licensespend.output import emit

app = typer.Typer(no_args_is_help=True, add_completion=False, help="SaaS License & Spend (draft reclaim pack).")


def _print(payload: object, ctx: typer.Context) -> None:
    human = bool((ctx.obj or {}).get("human"))
    typer.echo(emit(payload, human=human), nl=False)


@app.callback()
def _root(
    ctx: typer.Context,
    human: bool = typer.Option(False, "--human", help="Render a table instead of JSON."),
) -> None:
    ctx.obj = {"human": human}


def _register() -> None:
    from licensespend.audit.cli import app as audit_app
    from licensespend.github.cli import app as github_app
    from licensespend.loop.cli import app as loop_app
    from licensespend.m365.cli import app as m365_app
    from licensespend.renewals.cli import app as renewals_app
    from licensespend.report.cli import app as report_app
    from licensespend.shadow.cli import app as shadow_app
    from licensespend.slack.cli import app as slack_app
    from licensespend.usage.cli import app as usage_app

    app.add_typer(audit_app, name="audit")
    app.add_typer(m365_app, name="m365")
    app.add_typer(slack_app, name="slack")
    app.add_typer(github_app, name="github")
    app.add_typer(usage_app, name="usage")
    app.add_typer(shadow_app, name="shadow")
    app.add_typer(renewals_app, name="renewals")
    app.add_typer(report_app, name="report")
    app.add_typer(loop_app, name="loop")


_register()


def main() -> Any:
    app()
