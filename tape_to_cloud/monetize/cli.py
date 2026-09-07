"""Command-line interface for the monetize module.

Usage: ``python -m tape_to_cloud.monetize <subcommand> ...``. All state lives
in the directory given by ``--store`` (default ``output/tape_to_cloud/monetize/``).
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .access_control import AccessPolicyError, PolicyStore, render_aws_s3_policy
from .licensing import LICENSE_CLASSES, LicenseStore, LicenseTag, LicenseValidationError
from .royalties import (
    RATE_MODELS,
    RateCard,
    RoyaltyError,
    UsageLedger,
    compute_royalty_report,
    render_report_summary,
)

DEFAULT_STORE = "output/tape_to_cloud/monetize"


def _print_json(obj: object) -> None:
    print(json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True))


def _cmd_tag(args: argparse.Namespace) -> int:
    store = LicenseStore(args.store)
    tag = LicenseTag(
        asset_id=args.asset_id,
        license_id=args.license_id,
        license_class=args.license_class,
        rights=tuple(args.rights or ()),
        territory=args.territory,
        expires_at=args.expires_at,
        attribution_required=args.attribution_required,
        source_manifest_sha256=args.manifest_sha256,
        licensor_id=args.licensor_id,
    )
    store.add_tag(tag, actor=args.actor)
    _print_json(tag.to_dict())
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    store = LicenseStore(args.store)
    if args.license_class:
        tags = store.query_by_class(args.license_class)
    else:
        tags = store.load_tags()
    if args.asset_id:
        tags = [t for t in tags if t.asset_id == args.asset_id]
    _print_json([t.to_dict() for t in tags])
    return 0


def _cmd_policy(args: argparse.Namespace) -> int:
    policies = PolicyStore(args.store)
    if args.revoke:
        policy = policies.revoke(args.revoke, reason=args.reason, actor=args.actor)
        _print_json(policy)
        return 0
    licenses = LicenseStore(args.store)
    tag = licenses.latest_tag_for_asset(args.asset_id)
    if tag is None:
        print(f"error: no license tag found for asset {args.asset_id!r}", file=sys.stderr)
        return 2
    policy = policies.issue(
        tag,
        consumer_id=args.consumer_id,
        kms_key_id=args.kms_key_id,
        asset_prefixes=args.prefix or None,
        actor=args.actor,
    )
    if args.aws_bucket:
        _print_json(render_aws_s3_policy(policy, args.aws_bucket))
    else:
        _print_json(policy)
    return 0


def _cmd_record_usage(args: argparse.Namespace) -> int:
    ledger = UsageLedger(args.store)
    event = ledger.record(
        asset_id=args.asset_id,
        consumer_id=args.consumer_id,
        bytes_transferred=args.bytes,
        requests=args.requests,
        timestamp=args.timestamp,
        actor=args.actor,
    )
    _print_json(event)
    return 0


def _parse_rate_card(spec: str) -> RateCard:
    parts = spec.split(":")
    if len(parts) not in (3, 4):
        raise RoyaltyError(
            f"rate card must be LICENSE_ID:MODEL:RATE[:CURRENCY], got {spec!r}"
        )
    try:
        rate = Decimal(parts[2])
    except InvalidOperation as exc:
        raise RoyaltyError(f"invalid rate in rate card {spec!r}") from exc
    card = RateCard(
        license_id=parts[0],
        model=parts[1],
        rate=rate,
        currency=parts[3] if len(parts) == 4 else "USD",
    )
    return card.validate()


def _cmd_report(args: argparse.Namespace) -> int:
    ledger = UsageLedger(args.store)
    licenses = LicenseStore(args.store)
    cards = [_parse_rate_card(spec) for spec in args.rate_card]
    report = compute_royalty_report(
        ledger, licenses, cards, period_start=args.start, period_end=args.end
    )
    if args.json:
        _print_json(report)
    else:
        print(render_report_summary(report))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tape_to_cloud.monetize",
        description="Monetization broker layer: license tagging, access control, royalty reporting.",
    )
    parser.add_argument(
        "--store",
        default=DEFAULT_STORE,
        help=f"state directory (default: {DEFAULT_STORE})",
    )
    parser.add_argument("--actor", default=None, help="operator recorded in the audit log")
    sub = parser.add_subparsers(dest="command", required=True)

    p_tag = sub.add_parser("tag", help="add a per-asset license tag")
    p_tag.add_argument("--asset-id", required=True)
    p_tag.add_argument("--license-id", required=True)
    p_tag.add_argument("--license-class", required=True, choices=LICENSE_CLASSES)
    p_tag.add_argument("--right", dest="rights", action="append",
                       help="right granted (repeatable)")
    p_tag.add_argument("--territory", default="worldwide")
    p_tag.add_argument("--expires-at", default=None,
                       help="ISO-8601 UTC expiry (omit for perpetual)")
    p_tag.add_argument("--attribution-required", action="store_true")
    p_tag.add_argument("--manifest-sha256", required=True,
                       help="SHA-256 of the asset's source sidecar manifest")
    p_tag.add_argument("--licensor-id", default="unknown")
    p_tag.set_defaults(func=_cmd_tag)

    p_list = sub.add_parser("list", help="list/filter license tags")
    p_list.add_argument("--license-class", default=None, choices=LICENSE_CLASSES)
    p_list.add_argument("--asset-id", default=None)
    p_list.set_defaults(func=_cmd_list)

    p_policy = sub.add_parser("policy", help="generate or revoke an access policy")
    p_policy.add_argument("--asset-id")
    p_policy.add_argument("--consumer-id")
    p_policy.add_argument("--kms-key-id")
    p_policy.add_argument("--prefix", action="append",
                          help="asset prefix covered by the policy (repeatable)")
    p_policy.add_argument("--aws-bucket", default=None,
                          help="render as AWS-S3-style policy for this bucket")
    p_policy.add_argument("--revoke", metavar="POLICY_ID", default=None,
                          help="revoke an existing policy instead of issuing")
    p_policy.add_argument("--reason", default="explicit")
    p_policy.set_defaults(func=_cmd_policy)

    p_usage = sub.add_parser("record-usage", help="record an access/usage event")
    p_usage.add_argument("--asset-id", required=True)
    p_usage.add_argument("--consumer-id", required=True)
    p_usage.add_argument("--bytes", type=int, default=0)
    p_usage.add_argument("--requests", type=int, default=0)
    p_usage.add_argument("--timestamp", default=None, help="ISO-8601 UTC (default: now)")
    p_usage.set_defaults(func=_cmd_record_usage)

    p_report = sub.add_parser("report", help="compute a royalty report for a period")
    p_report.add_argument("--start", required=True, help="ISO-8601 UTC period start (inclusive)")
    p_report.add_argument("--end", required=True, help="ISO-8601 UTC period end (exclusive)")
    p_report.add_argument(
        "--rate-card",
        action="append",
        required=True,
        metavar="LICENSE_ID:MODEL:RATE[:CURRENCY]",
        help=f"rate card (repeatable); MODEL is one of {', '.join(RATE_MODELS)}",
    )
    p_report.add_argument("--json", action="store_true", help="emit the full report as JSON")
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "policy" and not args.revoke:
        missing = [
            name
            for name, value in (
                ("--asset-id", args.asset_id),
                ("--consumer-id", args.consumer_id),
                ("--kms-key-id", args.kms_key_id),
            )
            if not value
        ]
        if missing:
            parser.error(f"policy requires {', '.join(missing)} (or --revoke POLICY_ID)")
    Path(args.store).mkdir(parents=True, exist_ok=True)
    try:
        return args.func(args)
    except (LicenseValidationError, AccessPolicyError, RoyaltyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


__all__ = ["build_parser", "main"]
