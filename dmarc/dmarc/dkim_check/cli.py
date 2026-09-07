"""DKIM check CLI."""

from __future__ import annotations

import typer

from dmarc.config import DEFAULT_DKIM_SELECTORS
from dmarc.dkim_check.service import check_all_selectors, check_dkim

app = typer.Typer(help="DKIM record checks")


@app.command("check")
def check_cmd(
    domain: str = typer.Option(..., "--domain"),
    selector: str | None = typer.Option(None, "--selector"),
    all_selectors: bool = typer.Option(False, "--all-selectors"),
) -> None:
    """Check DKIM TXT at selector._domainkey.domain."""
    if all_selectors:
        findings = check_all_selectors(domain, list(DEFAULT_DKIM_SELECTORS))
        typer.echo(f"DKIM selectors checked: {len(findings)}")
        return
    sel = selector or "google"
    finding = check_dkim(domain, sel)
    typer.echo(f"DKIM {domain}/{sel}: key={finding.public_key_length} warnings={len(finding.warnings)}")
