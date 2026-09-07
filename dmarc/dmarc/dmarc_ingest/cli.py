"""DMARC ingest CLI."""

from __future__ import annotations

import typer

from dmarc.dmarc_ingest.service import ingest_reports

app = typer.Typer(help="DMARC aggregate report ingest")


@app.command("pull")
def pull_cmd(
    domain: str = typer.Option("example.com.au", "--domain"),
    imap_host: str | None = typer.Option(None, "--imap-host"),
    imap_user: str | None = typer.Option(None, "--imap-user"),
    demo: bool = typer.Option(False, "--demo", help="Load bundled sample RUA XML"),
) -> None:
    """Pull RUA from IMAP (DMARC_IMAP_PASS env) or sample fixtures."""
    import os

    if imap_host:
        os.environ["DMARC_IMAP_HOST"] = imap_host
    if imap_user:
        os.environ["DMARC_IMAP_USER"] = imap_user
    findings = ingest_reports(domain, demo=demo or not os.environ.get("DMARC_IMAP_PASS"))
    typer.echo(f"Ingested {len(findings)} aggregate rows for {domain}")
