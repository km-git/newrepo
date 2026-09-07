"""Inbox placement CLI."""

from __future__ import annotations

import typer

from dmarc.inbox_placement.service import DEFAULT_SEEDS, run_inbox_test

app = typer.Typer(help="Inbox placement heuristics")


@app.command("test")
def test_cmd(
    from_address: str = typer.Option(..., "--from"),
    to: str = typer.Option(",".join(s for _, s in DEFAULT_SEEDS), "--to"),
    live: bool = typer.Option(False, "--live"),
) -> None:
    """Send probe mail and record placement (demo mode without SMTP creds)."""
    seeds = [s.strip() for s in to.split(",") if s.strip()]
    findings = run_inbox_test(from_address, seeds, demo=not live)
    typer.echo(f"Inbox probes: {len(findings)}")
