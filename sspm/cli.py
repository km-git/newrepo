"""SSPM CLI — JSON by default; --human for tables."""

from __future__ import annotations

from pathlib import Path

import typer

from sspm.db.store import FindingsStore
from sspm.output import emit

app = typer.Typer(help="SSPM-as-report: read-only SaaS configuration posture")
discovery_app = typer.Typer(help="Tenant discovery")
audit_app = typer.Typer(help="Audit commands")
oauth_app = typer.Typer(help="OAuth grant inventory")
drift_app = typer.Typer(help="Config drift")
compliance_app = typer.Typer(help="Control reference mapping")
report_app = typer.Typer(help="Report generation")
tenant_app = typer.Typer(help="Multi-tenant registry")
disclaimer_app = typer.Typer(help="Disclaimers")
loop_app = typer.Typer(help="Improvement loop")
web_app = typer.Typer(help="Web UI")

app.add_typer(audit_app, name="audit")
app.add_typer(discovery_app, name="discovery")
app.add_typer(oauth_app, name="oauth-grants")
app.add_typer(drift_app, name="drift")
app.add_typer(compliance_app, name="compliance")
app.add_typer(report_app, name="report")
app.add_typer(tenant_app, name="tenant")
app.add_typer(disclaimer_app, name="disclaimers")
app.add_typer(loop_app, name="loop")
app.add_typer(web_app, name="web")


def _out(payload: object, human: bool) -> None:
    typer.echo(emit(payload, human=human))


@audit_app.command("inventory")
def audit_inventory(human: bool = typer.Option(False, "--human")) -> None:
    from sspm.audit.service import inventory

    _out(inventory(), human)


@discovery_app.command("m365")
def discovery_m365(
    tenant_id: str = typer.Option(..., "--tenant-id"),
    client_id: str | None = typer.Option(None, "--client-id"),
    client_secret: str | None = typer.Option(None, "--client-secret", envvar="M365_CLIENT_SECRET"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.m365_discovery.service import discover

    store = FindingsStore()
    _out(discover(tenant_id, client_id, client_secret, str(fixture) if fixture else None, store), human)


@discovery_app.command("gws")
def discovery_gws(
    domain: str = typer.Option(..., "--domain"),
    service_account: Path | None = typer.Option(None, "--service-account"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.google_workspace_discovery.service import discover

    store = FindingsStore()
    _out(
        discover(domain, str(service_account) if service_account else None, str(fixture) if fixture else None, store),
        human,
    )


@discovery_app.command("github")
def discovery_github(
    org: str = typer.Option(..., "--org"),
    token: str | None = typer.Option(None, "--token", envvar="GITHUB_TOKEN"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.github_discovery.service import discover

    store = FindingsStore()
    _out(discover(org, token, str(fixture) if fixture else None, store), human)


@discovery_app.command("slack")
def discovery_slack(
    workspace: str = typer.Option(..., "--workspace"),
    admin_token: str | None = typer.Option(None, "--admin-token", envvar="SLACK_ADMIN_TOKEN"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.slack_discovery.service import discover

    store = FindingsStore()
    _out(discover(workspace, admin_token, str(fixture) if fixture else None, store), human)


@discovery_app.command("okta")
def discovery_okta(
    org: str = typer.Option(..., "--org"),
    token: str | None = typer.Option(None, "--token", envvar="OKTA_TOKEN"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.okta_discovery.service import discover

    store = FindingsStore()
    _out(discover(org, token, str(fixture) if fixture else None, store), human)


@oauth_app.command("list")
def oauth_list(
    tenant: str = typer.Option("m365", "--tenant"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.oauth_grants.service import list_grants

    store = FindingsStore()
    _out(list_grants(tenant, str(fixture) if fixture else None, store), human)


@drift_app.command("diff")
def drift_diff(
    tenant: str = typer.Option(..., "--tenant"),
    baseline: Path | None = typer.Option(None, "--baseline"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.config_drift.service import diff

    _out(diff(tenant, str(baseline) if baseline else None), human)


@compliance_app.command("map")
def compliance_map(
    framework: str = typer.Option(..., "--framework"),
    tenant: str = typer.Option(..., "--tenant"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.compliance_map.service import map_framework

    _out(map_framework(framework, tenant), human)


@report_app.command("generate")
def report_generate(
    tenant: str = typer.Option(..., "--tenant"),
    output: Path = typer.Option(Path("output/sspm/report.md"), "--output"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.compliance_map.service import map_framework
    from sspm.config_drift.service import diff
    from sspm.m365_discovery.service import discover as m365_discover
    from sspm.oauth_grants.service import list_grants
    from sspm.report_writer.service import generate

    inv = m365_discover(tenant) if tenant == "m365" else {"tenant": tenant}
    drift = diff(tenant)
    oauth = list_grants(tenant)
    refs = map_framework("cis-m365" if tenant == "m365" else "iso27001", tenant)
    _out(generate(tenant, output, inventory=inv, drift=drift, oauth_grants=oauth, control_references=refs), human)


@tenant_app.command("add")
def tenant_add(
    name: str = typer.Option(..., "--name"),
    tenant_type: str = typer.Option(..., "--type"),
    client_id: str | None = typer.Option(None, "--client-id"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.multi_tenant.service import add_tenant

    _out(add_tenant(name, tenant_type, client_id), human)


@tenant_app.command("list")
def tenant_list(human: bool = typer.Option(False, "--human")) -> None:
    from sspm.multi_tenant.service import list_tenants

    _out(list_tenants(), human)


@disclaimer_app.command("show")
def disclaimers_show(
    name: str = typer.Option("disclaimer_au", "--name"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.disclaimers.service import show

    _out(show(name), human)


@loop_app.command("watch")
def loop_watch(
    fetch: bool = typer.Option(False, "--fetch"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.loop.watch import watch

    _out(watch(fetch=fetch), human)


@loop_app.command("monthly")
def loop_monthly(human: bool = typer.Option(False, "--human")) -> None:
    from sspm.loop.monthly import generate_monthly

    _out(generate_monthly(), human)


@loop_app.command("improve")
def loop_improve(
    fetch: bool = typer.Option(False, "--fetch"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from sspm.loop.improve import improve

    _out(improve(fetch=fetch), human)


@web_app.command("serve")
def web_serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host (use 0.0.0.0 for remote access)"),
    port: int = typer.Option(8766, "--port"),
) -> None:
    import uvicorn

    from sspm.web.app import app as fastapi_app

    typer.echo(f"SSPM Web UI: http://127.0.0.1:{port}/")
    uvicorn.run(fastapi_app, host=host, port=port, log_level="info")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
