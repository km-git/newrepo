"""DNS check CLI."""

from __future__ import annotations

import typer

from dmarc.dns_check.service import check_domain

app = typer.Typer(help="DNS record checks")


@app.command("check")
def check_cmd(domain: str = typer.Option(..., "--domain")) -> None:
    """Check A/AAAA/MX/TXT/CNAME, SPF, DKIM, DMARC, MTA-STS, TLS-RPT, BIMI."""
    findings = check_domain(domain)
    typer.echo(f"DNS findings: {len(findings)} records for {domain}")
