"""Cloud Cost & Configuration Review CLI."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from cost.output import emit

app = typer.Typer(
    name="cost",
    help="Cloud Cost & Configuration Review — read-only cost + configuration reports",
    no_args_is_help=True,
)

audit_app = typer.Typer(help="Workspace + OSS inventory")
inventory_app = typer.Typer(help="Cloud resource inventory")
cost_app = typer.Typer(help="Cost rollups")
rightsizing_app = typer.Typer(help="Rightsizing recommendations")
untagged_app = typer.Typer(help="Untagged resource inventory")
drift_app = typer.Typer(help="Configuration drift")
compliance_app = typer.Typer(help="Framework reference mapping")
report_app = typer.Typer(help="Report generation")
loop_app = typer.Typer(help="5-stage improvement loop")

app.add_typer(audit_app, name="audit")
app.add_typer(inventory_app, name="inventory")
app.add_typer(cost_app, name="cost-explorer")
app.add_typer(rightsizing_app, name="rightsizing")
app.add_typer(untagged_app, name="untagged")
app.add_typer(drift_app, name="drift")
app.add_typer(compliance_app, name="compliance")
app.add_typer(report_app, name="report")
app.add_typer(loop_app, name="loop")


def _print(payload: object, human: bool = False) -> None:
    typer.echo(emit(payload, human=human))


@audit_app.command("inventory")
def audit_inventory(human: bool = typer.Option(False, "--human")) -> None:
    from cost.audit.service import inventory

    _print(inventory(), human)


@inventory_app.command("aws")
def inventory_aws(
    profile: str | None = typer.Option(None, "--profile"),
    regions: str | None = typer.Option("ap-southeast-2", "--regions"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.aws_inventory.service import scan_aws

    region_list = [r.strip() for r in (regions or "").split(",") if r.strip()]
    _print(scan_aws(profile=profile, regions=region_list, fixture=fixture), human)


@inventory_app.command("azure")
def inventory_azure(
    subscription_id: str | None = typer.Option(None, "--subscription-id"),
    tenant_id: str | None = typer.Option(None, "--tenant-id"),
    client_id: str | None = typer.Option(None, "--client-id"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.azure_inventory.service import scan_azure

    _print(
        scan_azure(
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            client_id=client_id,
            fixture=fixture,
        ),
        human,
    )


@inventory_app.command("gcp")
def inventory_gcp(
    project_id: str | None = typer.Option(None, "--project-id"),
    service_account: str | None = typer.Option(None, "--service-account"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.gcp_inventory.service import scan_gcp

    _print(scan_gcp(project_id=project_id, service_account=service_account, fixture=fixture), human)


@cost_app.command("rollup")
def cost_explorer(
    provider: str = typer.Option("aws", "--provider"),
    since: str = typer.Option("30d", "--since"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.cost_explorer.service import explore

    _print(explore(provider=provider, since=since, fixture=fixture), human)


@rightsizing_app.command("scan")
def rightsizing_scan(
    provider: str = typer.Option("aws", "--provider"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.rightsizing.service import scan

    _print(scan(provider=provider, fixture=fixture), human)


@untagged_app.command("scan")
def untagged_scan(
    policy: Path | None = typer.Option(None, "--tagging-policy"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.untagged.service import scan

    _print(scan(policy_path=policy, fixture=fixture), human)


@drift_app.command("diff")
def drift_diff(
    provider: str = typer.Option("aws", "--provider"),
    baseline: Path | None = typer.Option(None, "--baseline"),
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.config_drift.service import diff

    _print(diff(provider=provider, baseline_path=baseline, fixture=fixture), human)


@compliance_app.command("map")
def compliance_map(
    framework: str = typer.Option("finops-foundation", "--framework"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.compliance_map.service import map_findings

    _print(map_findings(framework=framework), human)


@report_app.command("generate")
def report_generate(
    provider: str = typer.Option("aws", "--provider"),
    since: str = typer.Option("30d", "--since"),
    output: Path | None = typer.Option(None, "--output"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.report_writer.service import generate

    out = output or Path("output/cost/report.md")
    _print(generate(provider=provider, since=since, output=out), human)


@app.command("multi-account")
def multi_account_run(
    fixture: Path | None = typer.Option(None, "--fixture"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.multi_account.service import run_accounts

    _print(run_accounts(fixture=fixture), human)


@loop_app.command("watch")
def loop_watch(
    fetch: bool = typer.Option(False, "--fetch"),
    human: bool = typer.Option(False, "--human"),
) -> None:
    from cost.loop.watch import watch

    _print(watch(fetch=fetch), human)


@loop_app.command("monthly")
def loop_monthly(human: bool = typer.Option(False, "--human")) -> None:
    from cost.loop.monthly import generate_monthly

    _print(generate_monthly(), human)


@app.command("webui")
def webui_serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8766, "--port"),
    static: bool = typer.Option(False, "--static"),
) -> None:
    from cost.webui.service import run_server, run_static

    if static:
        path = run_static()
        typer.echo(json.dumps({"static_html": str(path)}, indent=2))
    else:
        run_server(host=host, port=port)


if __name__ == "__main__":
    app()


def main(argv: list[str] | None = None) -> int:
    """Argparse-compatible entry for cost.loop delegation."""
    try:
        if argv is None:
            app()
        else:
            app(args=argv, prog_name="cost")
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return int(code) if isinstance(code, int) else 1
    return 0
