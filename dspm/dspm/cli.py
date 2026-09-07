"""DSPM top-level Typer CLI."""

from __future__ import annotations

import typer

from dspm.audit.cli import app as audit_app
from dspm.access.cli import app as access_app
from dspm.ai_security.cli import app as ai_security_app
from dspm.classification.cli import app as classification_app
from dspm.compliance.cli import app as compliance_app
from dspm.custom_types.cli import app as custom_types_app
from dspm.discovery.cli import app as discovery_app
from dspm.encryption_check.cli import app as encryption_app
from dspm.exposure.cli import app as exposure_app
from dspm.remediation.cli import app as remediation_app
from dspm.risk.cli import app as risk_app
from dspm.shadow.cli import app as shadow_app

app = typer.Typer(name="dspm", help="Cyera-like DSPM from OSS components")
app.add_typer(audit_app, name="audit")
app.add_typer(discovery_app, name="discovery")
app.add_typer(classification_app, name="classify")
app.add_typer(risk_app, name="risk")
app.add_typer(access_app, name="access")
app.add_typer(exposure_app, name="exposure")
app.add_typer(encryption_app, name="encryption-check")
app.add_typer(shadow_app, name="shadow")
app.add_typer(custom_types_app, name="custom-types")
app.add_typer(compliance_app, name="compliance")
app.add_typer(ai_security_app, name="ai-security")
app.add_typer(remediation_app, name="remediate")


@app.command("version")
def version() -> None:
    """Print DSPM version."""
    from dspm import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
