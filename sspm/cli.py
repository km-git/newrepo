"""SSPM CLI. JSON by default; pass --human for a table.

Entry point: `sspm = "sspm.cli:app"` (Typer if installed, else argparse).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from sspm.output import emit


def _store(ns: argparse.Namespace):
    from sspm.db.store import FindingsStore

    path = Path(ns.db) if getattr(ns, "db", None) else None
    return FindingsStore(path)


def _print(payload: object, ns: argparse.Namespace) -> int:
    text = emit(payload, human=bool(getattr(ns, "human", False)))
    sys.stdout.write(text + ("\n" if not text.endswith("\n") else ""))
    return 0


def _cmd_audit_inventory(ns: argparse.Namespace) -> int:
    from sspm.audit.service import inventory

    return _print(inventory(init_db=True), ns)


def _cmd_discovery_m365(ns: argparse.Namespace) -> int:
    from sspm.m365_discovery.service import discover_m365

    payload = discover_m365(
        tenant_id=ns.tenant_id,
        client_id=ns.client_id,
        client_secret_env=ns.client_secret,
        tenant_name=ns.name or "m365-demo",
        fixture=Path(ns.fixture) if ns.fixture else None,
        store=_store(ns) if ns.persist else None,
    )
    return _print(payload, ns)


def _cmd_discovery_gws(ns: argparse.Namespace) -> int:
    from sspm.google_workspace_discovery.service import discover_gws

    return _print(
        discover_gws(
            domain=ns.domain,
            service_account=ns.service_account,
            tenant_name=ns.name or ns.domain or "gws-demo",
            fixture=Path(ns.fixture) if ns.fixture else None,
            store=_store(ns) if ns.persist else None,
        ),
        ns,
    )


def _cmd_discovery_github(ns: argparse.Namespace) -> int:
    from sspm.github_discovery.service import discover_github

    return _print(
        discover_github(
            org=ns.org,
            token_env=ns.token,
            tenant_name=ns.name or ns.org or "github-demo",
            fixture=Path(ns.fixture) if ns.fixture else None,
            store=_store(ns) if ns.persist else None,
        ),
        ns,
    )


def _cmd_discovery_slack(ns: argparse.Namespace) -> int:
    from sspm.slack_discovery.service import discover_slack

    return _print(
        discover_slack(
            workspace=ns.workspace,
            admin_token_env=ns.admin_token,
            tenant_name=ns.name or ns.workspace or "slack-demo",
            fixture=Path(ns.fixture) if ns.fixture else None,
            store=_store(ns) if ns.persist else None,
        ),
        ns,
    )


def _cmd_discovery_okta(ns: argparse.Namespace) -> int:
    from sspm.okta_discovery.service import discover_okta

    return _print(
        discover_okta(
            org=ns.org,
            token_env=ns.token,
            tenant_name=ns.name or ns.org or "okta-demo",
            fixture=Path(ns.fixture) if ns.fixture else None,
            store=_store(ns) if ns.persist else None,
        ),
        ns,
    )


def _cmd_oauth(ns: argparse.Namespace) -> int:
    from sspm.oauth_grants.service import list_grants_dicts

    return _print(
        list_grants_dicts(
            tenant=ns.tenant,
            tenant_name=ns.name,
            store=_store(ns) if ns.persist else None,
        ),
        ns,
    )


def _cmd_drift(ns: argparse.Namespace) -> int:
    from sspm.config_drift.service import diff_tenant

    rows = diff_tenant(
        tenant=ns.tenant,
        tenant_name=ns.name,
        baseline=Path(ns.baseline) if ns.baseline else None,
        store=_store(ns) if ns.persist else None,
    )
    return _print([r.model_dump() for r in rows], ns)


def _cmd_compliance(ns: argparse.Namespace) -> int:
    from sspm.compliance_map.service import map_tenant

    rows = map_tenant(
        framework=ns.framework,
        tenant=ns.tenant,
        tenant_name=ns.name,
        store=_store(ns) if ns.persist else None,
    )
    return _print([r.model_dump() for r in rows], ns)


def _cmd_report(ns: argparse.Namespace) -> int:
    from sspm.report_writer.service import generate

    result = generate(tenant=ns.tenant, tenant_name=ns.name, output=Path(ns.output) if ns.output else None)
    return _print(result.model_dump(), ns)


def _cmd_tenant_add(ns: argparse.Namespace) -> int:
    from sspm.multi_tenant.service import add_tenant

    tenant = add_tenant(
        name=ns.name,
        tenant_type=ns.type,
        client_id=ns.client_id,
        store=_store(ns) if ns.persist else None,
    )
    return _print(tenant.model_dump(), ns)


def _cmd_tenant_list(ns: argparse.Namespace) -> int:
    from sspm.multi_tenant.service import list_tenants, next_run

    rows = []
    for tenant in list_tenants():
        payload = tenant.model_dump()
        payload["next_run"] = next_run(tenant.cron_expr, tenant.timezone)
        rows.append(payload)
    return _print(rows, ns)


def _cmd_disclaimers(ns: argparse.Namespace) -> int:
    from sspm.disclaimers.service import show

    return _print(show(ns.name).model_dump(), ns)


def _cmd_loop_watch(ns: argparse.Namespace) -> int:
    from sspm.loop.watch import watch

    return _print(watch(mode=ns.mode, fetch=ns.fetch), ns)


def _cmd_loop_monthly(ns: argparse.Namespace) -> int:
    from sspm.loop.monthly import generate_monthly

    return _print(generate_monthly(), ns)


def _cmd_web(ns: argparse.Namespace) -> int:
    from sspm.web.app import run, write_static

    if ns.static:
        return _print(write_static(), ns)
    run(host=ns.host, port=ns.port)
    return 0


def _cmd_demo(ns: argparse.Namespace) -> int:
    """End-to-end fixture run used by `make sspm-all`."""
    from sspm.audit.service import inventory
    from sspm.compliance_map.service import map_tenant
    from sspm.config_drift.service import diff_tenant
    from sspm.disclaimers.service import show
    from sspm.github_discovery.service import discover_github
    from sspm.google_workspace_discovery.service import discover_gws
    from sspm.loop.monthly import generate_monthly
    from sspm.loop.watch import watch
    from sspm.m365_discovery.service import discover_m365
    from sspm.multi_tenant.service import add_tenant, list_tenants
    from sspm.oauth_grants.service import list_grants_dicts
    from sspm.okta_discovery.service import discover_okta
    from sspm.report_writer.service import generate
    from sspm.slack_discovery.service import discover_slack

    store = _store(ns) if ns.persist else None
    inv = inventory(init_db=True)
    discover_m365(store=store)
    discover_gws(store=store)
    discover_github(store=store)
    discover_slack(store=store)
    discover_okta(store=store)
    with contextlib.suppress(ValueError):
        add_tenant(name="demo-m365", tenant_type="m365", store=store)
    reports = {
        "m365": generate(
            tenant="m365", tenant_name="m365-demo", output=Path("output/sspm/m365_report.md")
        ).model_dump(),
        "gws": generate(tenant="gws", tenant_name="gws-demo", output=Path("output/sspm/gws_report.md")).model_dump(),
        "github": generate(
            tenant="github", tenant_name="github-demo", output=Path("output/sspm/github_report.md")
        ).model_dump(),
        "slack": generate(
            tenant="slack", tenant_name="slack-demo", output=Path("output/sspm/slack_report.md")
        ).model_dump(),
        "okta": generate(
            tenant="okta", tenant_name="okta-demo", output=Path("output/sspm/okta_report.md")
        ).model_dump(),
    }
    payload = {
        "inventory": {"tool_count": inv["tool_count"], "written": inv.get("written")},
        "tenants": [t.model_dump() for t in list_tenants()],
        "oauth": list_grants_dicts(tenant="all", store=store),
        "drift_m365": [d.model_dump() for d in diff_tenant(tenant="m365", store=store)],
        "control_refs_m365": [r.model_dump() for r in map_tenant(framework="cis-m365", tenant="m365", store=store)],
        "disclaimer": show().name,
        "watch": watch(mode="offline"),
        "monthly": generate_monthly(),
        "reports": reports,
    }
    dest = Path(ns.output) if ns.output else Path("output/sspm/demo_run.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    payload["written"] = str(dest)
    return _print(payload, ns)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sspm", description="SSPM Configuration & Inventory Report CLI")
    parser.add_argument("--human", action="store_true", help="pretty table instead of JSON")
    parser.add_argument("--db", default=None, help="SQLite path (default output/sspm/sspm.sqlite or SSPM_DB)")
    parser.add_argument("--persist", action="store_true", help="write results to the findings DB")
    sub = parser.add_subparsers(dest="cmd", required=True)

    audit = sub.add_parser("audit")
    audit_sub = audit.add_subparsers(dest="audit_cmd", required=True)
    inv = audit_sub.add_parser("inventory")
    inv.set_defaults(func=_cmd_audit_inventory)

    disc = sub.add_parser("discovery")
    disc_sub = disc.add_subparsers(dest="disc_cmd", required=True)

    m365 = disc_sub.add_parser("m365")
    m365.add_argument("--tenant-id")
    m365.add_argument("--client-id")
    m365.add_argument("--client-secret", default="M365_CLIENT_SECRET")
    m365.add_argument("--name")
    m365.add_argument("--fixture")
    m365.set_defaults(func=_cmd_discovery_m365)

    gws = disc_sub.add_parser("gws")
    gws.add_argument("--domain")
    gws.add_argument("--service-account")
    gws.add_argument("--name")
    gws.add_argument("--fixture")
    gws.set_defaults(func=_cmd_discovery_gws)

    gh = disc_sub.add_parser("github")
    gh.add_argument("--org")
    gh.add_argument("--token", default="GITHUB_TOKEN")
    gh.add_argument("--name")
    gh.add_argument("--fixture")
    gh.set_defaults(func=_cmd_discovery_github)

    slack = disc_sub.add_parser("slack")
    slack.add_argument("--workspace")
    slack.add_argument("--admin-token", default="SLACK_ADMIN_TOKEN")
    slack.add_argument("--name")
    slack.add_argument("--fixture")
    slack.set_defaults(func=_cmd_discovery_slack)

    okta = disc_sub.add_parser("okta")
    okta.add_argument("--org")
    okta.add_argument("--token", default="OKTA_TOKEN")
    okta.add_argument("--name")
    okta.add_argument("--fixture")
    okta.set_defaults(func=_cmd_discovery_okta)

    oauth = sub.add_parser("oauth-grants")
    oauth_sub = oauth.add_subparsers(dest="oauth_cmd", required=True)
    oauth_list = oauth_sub.add_parser("list")
    oauth_list.add_argument("--tenant", default="m365")
    oauth_list.add_argument("--name")
    oauth_list.set_defaults(func=_cmd_oauth)

    drift = sub.add_parser("drift")
    drift_sub = drift.add_subparsers(dest="drift_cmd", required=True)
    drift_diff = drift_sub.add_parser("diff")
    drift_diff.add_argument("--tenant", default="m365")
    drift_diff.add_argument("--name")
    drift_diff.add_argument("--baseline")
    drift_diff.set_defaults(func=_cmd_drift)

    comp = sub.add_parser("compliance")
    comp_sub = comp.add_subparsers(dest="comp_cmd", required=True)
    comp_map = comp_sub.add_parser("map")
    comp_map.add_argument("--framework", default="cis-m365")
    comp_map.add_argument("--tenant", default="m365")
    comp_map.add_argument("--name")
    comp_map.set_defaults(func=_cmd_compliance)

    report = sub.add_parser("report")
    report_sub = report.add_subparsers(dest="report_cmd", required=True)
    report_gen = report_sub.add_parser("generate")
    report_gen.add_argument("--tenant", default="m365")
    report_gen.add_argument("--name")
    report_gen.add_argument("--output")
    report_gen.set_defaults(func=_cmd_report)

    tenant = sub.add_parser("tenant")
    tenant_sub = tenant.add_subparsers(dest="tenant_cmd", required=True)
    t_add = tenant_sub.add_parser("add")
    t_add.add_argument("--name", required=True)
    t_add.add_argument("--type", required=True)
    t_add.add_argument("--client-id")
    t_add.set_defaults(func=_cmd_tenant_add)
    t_list = tenant_sub.add_parser("list")
    t_list.set_defaults(func=_cmd_tenant_list)

    discm = sub.add_parser("disclaimers")
    discm_sub = discm.add_subparsers(dest="disc_cmd2", required=True)
    d_show = discm_sub.add_parser("show")
    d_show.add_argument("--name", default="disclaimer_au")
    d_show.set_defaults(func=_cmd_disclaimers)

    loop = sub.add_parser("loop")
    loop_sub = loop.add_subparsers(dest="loop_cmd", required=True)
    lw = loop_sub.add_parser("watch")
    lw.add_argument("--mode", default="offline")
    lw.add_argument("--fetch", action="store_true")
    lw.set_defaults(func=_cmd_loop_watch)
    lm = loop_sub.add_parser("monthly")
    lm.set_defaults(func=_cmd_loop_monthly)

    web = sub.add_parser("web")
    web.add_argument("--host", default="0.0.0.0")
    web.add_argument("--port", type=int, default=8767)
    web.add_argument("--static", action="store_true")
    web.set_defaults(func=_cmd_web)

    demo = sub.add_parser("demo")
    demo.add_argument("--output")
    demo.set_defaults(func=_cmd_demo)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(list(argv) if argv is not None else None)
    return int(ns.func(ns))


def app() -> None:
    """Console-script entry (`sspm = sspm.cli:app`)."""
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
