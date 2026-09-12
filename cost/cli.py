"""Typer-compatible argparse CLI: `cost` / `python -m cost`."""

from __future__ import annotations

import argparse
import json
from typing import Any

from cost import __version__


def _dump(payload: Any) -> None:
    print(json.dumps(payload, indent=2, default=str, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cost", description="Cloud Cost & Configuration Review")
    parser.add_argument("--version", action="version", version=f"cost {__version__}")
    parser.add_argument("--sandbox", action="store_true", default=True, help="Use fixtures (default)")
    parser.add_argument("--live", action="store_true", help="Attempt customer cloud APIs")
    sub = parser.add_subparsers(dest="cmd", required=True)

    audit = sub.add_parser("audit", help="Workspace tool inventory")
    audit_sub = audit.add_subparsers(dest="audit_cmd", required=True)
    audit_sub.add_parser("inventory", help="Write cost-inventory.json")

    inv = sub.add_parser("inventory", help="Cloud resource inventory (read-only)")
    inv_sub = inv.add_subparsers(dest="inventory_cmd", required=True)
    aws = inv_sub.add_parser("aws")
    aws.add_argument("--profile", default="")
    aws.add_argument("--regions", default="ap-southeast-2")
    az = inv_sub.add_parser("azure")
    az.add_argument("--subscription-id", default="")
    az.add_argument("--tenant-id", default="")
    az.add_argument("--client-id", default="")
    gcp = inv_sub.add_parser("gcp")
    gcp.add_argument("--project-id", default="")
    gcp.add_argument("--service-account", default="")

    ce = sub.add_parser("cost-explorer", help="Cost rollup")
    ce.add_argument("--provider", default="all")
    ce.add_argument("--since", default="30d")

    rs = sub.add_parser("rightsizing", help="Rightsizing observations")
    rs_sub = rs.add_subparsers(dest="rs_cmd", required=True)
    rs_scan = rs_sub.add_parser("scan")
    rs_scan.add_argument("--provider", default="all")

    un = sub.add_parser("untagged", help="Untagged inventory")
    un_sub = un.add_subparsers(dest="un_cmd", required=True)
    un_scan = un_sub.add_parser("scan")
    un_scan.add_argument("--tagging-policy", default="")
    un_scan.add_argument("--provider", default="all")

    drift = sub.add_parser("drift", help="Cost-relevant config drift")
    drift_sub = drift.add_subparsers(dest="drift_cmd", required=True)
    drift_diff = drift_sub.add_parser("diff")
    drift_diff.add_argument("--provider", default="all")
    drift_diff.add_argument("--baseline", default="")

    fw = sub.add_parser("compliance", help="Map observations to a framework (mapping only)")
    fw_sub = fw.add_subparsers(dest="fw_cmd", required=True)
    fw_map = fw_sub.add_parser("map")
    fw_map.add_argument("--framework", default="finops-foundation")

    report = sub.add_parser("report", help="Write report.md / report.json")
    report_sub = report.add_subparsers(dest="report_cmd", required=True)
    report_gen = report_sub.add_parser("generate")
    report_gen.add_argument("--provider", default="all")
    report_gen.add_argument("--since", default="30d")
    report_gen.add_argument("--output", default="")

    ui = sub.add_parser("ui", help="Stdlib Web UI (or --static HTML)")
    ui.add_argument("--host", default="0.0.0.0")
    ui.add_argument("--port", type=int, default=8765)
    ui.add_argument("--static", action="store_true")
    ui.add_argument("--sandbox", action="store_true", default=True)

    scan = sub.add_parser("scan-all", help="Run every module end-to-end")
    scan.add_argument("--provider", default="all")
    scan.add_argument("--since", default="30d")
    scan.add_argument("--sandbox", action="store_true", default=True)

    monthly = sub.add_parser("monthly", help="Write monthly/YYYY-MM.md and cost-trend.md")
    monthly.add_argument("--noop", action="store_true")

    sub.add_parser("multi-account", help="Aggregate c7n-org dry-run accounts")
    return parser


def _sandbox(args: argparse.Namespace) -> bool:
    return not bool(getattr(args, "live", False))


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    sandbox = _sandbox(args)
    cmd = args.cmd
    if cmd == "audit":
        from cost.audit.service import run

        return run(sandbox=sandbox)
    if cmd == "inventory" and args.inventory_cmd == "aws":
        from cost.aws_inventory.service import run

        return run(sandbox=sandbox, profile=args.profile, regions=args.regions)
    if cmd == "inventory" and args.inventory_cmd == "azure":
        from cost.azure_inventory.service import run

        return run(
            sandbox=sandbox,
            subscription_id=args.subscription_id,
            tenant_id=args.tenant_id,
            client_id=args.client_id,
        )
    if cmd == "inventory" and args.inventory_cmd == "gcp":
        from cost.gcp_inventory.service import run

        return run(sandbox=sandbox, project_id=args.project_id, service_account=args.service_account)
    if cmd == "cost-explorer":
        from cost.cost_explorer.service import run

        return run(sandbox=sandbox, provider=args.provider, since=args.since)
    if cmd == "rightsizing":
        from cost.rightsizing.service import run

        return run(sandbox=sandbox, provider=args.provider)
    if cmd == "untagged":
        from cost.untagged.service import run

        return run(sandbox=sandbox, tagging_policy=args.tagging_policy, provider=args.provider)
    if cmd == "drift":
        from cost.config_drift.service import run

        return run(sandbox=sandbox, provider=args.provider, baseline=args.baseline)
    if cmd == "compliance":
        from cost.compliance_map.service import run

        return run(sandbox=sandbox, framework=args.framework)
    if cmd == "report":
        from cost.report_writer.service import run

        return run(sandbox=sandbox, provider=args.provider, since=args.since, output=args.output)
    if cmd == "scan-all":
        from cost.pipeline import run_all

        return run_all(sandbox=sandbox, provider=args.provider, since=args.since)
    if cmd == "monthly":
        from cost.loop.service import monthly_rollup

        return monthly_rollup()
    if cmd == "multi-account":
        from cost.multi_account.service import run

        return run(sandbox=sandbox)
    if cmd == "ui":
        from cost.webui.server import run_ui

        return run_ui(host=args.host, port=args.port, static=args.static, sandbox=sandbox)
    raise SystemExit(f"unknown command {cmd}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = dispatch(args)
    if args.cmd == "ui" and not args.static:
        return 0
    _dump(payload)
    return 0 if payload.get("ok", True) else 1


def app() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    app()
