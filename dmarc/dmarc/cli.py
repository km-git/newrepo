"""DMARC top-level Typer CLI."""

from __future__ import annotations

import typer

from dmarc.aggregate_report.cli import app as aggregate_app
from dmarc.audit.cli import app as audit_app
from dmarc.dkim_check.cli import app as dkim_app
from dmarc.dmarc_ingest.cli import app as ingest_app
from dmarc.dns_check.cli import app as dns_app
from dmarc.forensic_report.cli import app as forensic_app
from dmarc.inbox_placement.cli import app as inbox_app
from dmarc.report_writer.cli import app as report_app
from dmarc.spf_parser.cli import app as spf_app
from dmarc.web.cli import app as web_app

app = typer.Typer(name="dmarc", help="Email Deliverability & Brand-Protection Monitor")
app.add_typer(audit_app, name="audit")
app.add_typer(dns_app, name="dns")
app.add_typer(spf_app, name="spf")
app.add_typer(dkim_app, name="dkim")
app.add_typer(ingest_app, name="ingest")
app.add_typer(aggregate_app, name="aggregate")
app.add_typer(forensic_app, name="forensic")
app.add_typer(inbox_app, name="inbox")
app.add_typer(report_app, name="report")
app.add_typer(web_app, name="web")


@app.command("version")
def version_cmd() -> None:
    from dmarc import __version__

    typer.echo(__version__)


@app.command("scan")
def scan_cmd(domain: str = typer.Option("example.com.au", "--domain")) -> None:
    """Run DNS + SPF + DKIM + sample ingest + report in one shot."""
    from dmarc.config import DEFAULT_DKIM_SELECTORS
    from dmarc.dkim_check.service import check_all_selectors
    from dmarc.dmarc_ingest.service import ingest_reports
    from dmarc.dns_check.service import check_domain
    from dmarc.inbox_placement.service import run_inbox_test
    from dmarc.report_writer.service import generate_report
    from dmarc.spf_parser.service import parse_spf

    check_domain(domain)
    parse_spf(domain)
    check_all_selectors(domain, list(DEFAULT_DKIM_SELECTORS))
    ingest_reports(domain, demo=True)
    run_inbox_test(f"noreply@{domain}", ["seed@gmail.com"], demo=True)
    md, _ = generate_report(domain)
    typer.echo(f"Scan complete → {md}")


if __name__ == "__main__":
    app()
