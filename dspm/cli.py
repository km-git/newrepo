"""DSPM CLI. JSON by default; pass --human for a table."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from dspm.output import emit


def _store(ns: argparse.Namespace):
    from dspm.db.store import FindingsStore

    path = Path(ns.db) if getattr(ns, "db", None) else None
    return FindingsStore(path)


def _print(payload: object, ns: argparse.Namespace) -> int:
    text = emit(payload, human=bool(getattr(ns, "human", False)))
    sys.stdout.write(text + ("\n" if not text.endswith("\n") else ""))
    return 0


def _cmd_audit_inventory(ns: argparse.Namespace) -> int:
    from dspm.audit.service import inventory

    return _print(inventory(), ns)


def _cmd_discovery_dir(ns: argparse.Namespace) -> int:
    from dspm.discovery.service import discover_directory

    stores = discover_directory(ns.path, store=_store(ns) if ns.persist else None)
    return _print([s.model_dump() for s in stores], ns)


def _cmd_discovery_cloud(ns: argparse.Namespace) -> int:
    from dspm.discovery.service import discover_cloud

    stores = discover_cloud(ns.provider, profile=ns.profile, fixture=ns.fixture)
    return _print([s.model_dump() for s in stores], ns)


def _cmd_classify(ns: argparse.Namespace) -> int:
    from dspm.classification.service import classify_path

    result = classify_path(ns.path, limit=ns.limit, store=_store(ns) if ns.persist else None)
    return _print(result.model_dump(), ns)


def _cmd_classify_postgres(ns: argparse.Namespace) -> int:
    from dspm.classification.service import classify_postgres_stub

    return _print(classify_postgres_stub(ns.table), ns)


def _cmd_risk(ns: argparse.Namespace) -> int:
    from dspm.risk.service import score_findings, score_store

    store = _store(ns)
    if ns.fixture:
        findings = json.loads(Path(ns.fixture).read_text(encoding="utf-8"))
        ranked = score_findings(findings, store=store if ns.persist else None)
    else:
        ranked = score_store(store)
    payload = [r.model_dump() for r in ranked]
    if ns.since:
        payload = [{"since": ns.since, **row} for row in payload]
    return _print(payload, ns)


def _cmd_access(ns: argparse.Namespace) -> int:
    from dspm.access.service import map_access

    edges = map_access(store_id=ns.store_id, fixture=ns.fixture, db=_store(ns) if ns.persist else None)
    return _print([e.model_dump() for e in edges], ns)


def _cmd_exposure(ns: argparse.Namespace) -> int:
    from dspm.exposure.service import scan_exposure

    items = scan_exposure(provider=ns.provider, fixture=ns.fixture, store=_store(ns) if ns.persist else None)
    return _print([i.model_dump() for i in items], ns)


def _cmd_encryption(ns: argparse.Namespace) -> int:
    from dspm.encryption_check.service import scan_path

    items = scan_path(ns.path, fixture=ns.fixture, store=_store(ns) if ns.persist else None)
    return _print([i.model_dump() for i in items], ns)


def _cmd_shadow(ns: argparse.Namespace) -> int:
    from dspm.shadow.service import scan_shadow

    items = scan_shadow(path=ns.path, provider=ns.provider, store=_store(ns) if ns.persist else None)
    return _print([i.model_dump() for i in items], ns)


def _cmd_custom_list(ns: argparse.Namespace) -> int:
    from dspm.custom_types.service import load_registry

    return _print([t.model_dump() for t in load_registry().types], ns)


def _cmd_custom_test(ns: argparse.Namespace) -> int:
    from dspm.custom_types.service import test_type

    return _print(test_type(ns.type, ns.sample), ns)


def _cmd_compliance(ns: argparse.Namespace) -> int:
    from dspm.compliance.service import map_findings

    store = _store(ns)
    findings = store.fetchall("findings")
    if ns.fixture:
        findings = json.loads(Path(ns.fixture).read_text(encoding="utf-8"))
    hits = map_findings(findings, framework=ns.framework, store=store if ns.persist else None)
    return _print([h.model_dump() for h in hits], ns)


def _cmd_ai_export(ns: argparse.Namespace) -> int:
    from dspm.ai_security.service import scan_export

    items = scan_export(ns.path, store=_store(ns) if ns.persist else None)
    return _print([i.model_dump() for i in items], ns)


def _cmd_ai_uri(ns: argparse.Namespace) -> int:
    from dspm.ai_security.service import scan_vectorstore_uri

    return _print(scan_vectorstore_uri(ns.uri), ns)


def _cmd_remediate_plan(ns: argparse.Namespace) -> int:
    from dspm.remediation.service import plan

    items = plan(dry_run=ns.dry_run, store=_store(ns) if ns.persist else None)
    return _print([i.model_dump() for i in items], ns)


def _cmd_remediate_apply(ns: argparse.Namespace) -> int:
    from dspm.remediation.service import apply_policy

    return _print(apply_policy(ns.policy, limit=ns.limit, dry_run=not ns.apply), ns)


def _cmd_loop_watch(ns: argparse.Namespace) -> int:
    from dspm.loop.watch import watch

    return _print(watch(mode=ns.mode, fetch=ns.fetch), ns)


def _cmd_loop_monthly(ns: argparse.Namespace) -> int:
    from dspm.loop.monthly import generate_monthly

    return _print(generate_monthly(), ns)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dspm", description="OSS DSPM (Cyera-like) CLI")
    parser.add_argument("--human", action="store_true", help="pretty table instead of JSON")
    parser.add_argument("--db", default=None, help="SQLite path (default output/dspm/dspm.sqlite or DSPM_DB)")
    parser.add_argument("--persist", action="store_true", help="write results to the findings DB")
    sub = parser.add_subparsers(dest="cmd", required=True)

    audit = sub.add_parser("audit")
    audit_sub = audit.add_subparsers(dest="audit_cmd", required=True)
    inv = audit_sub.add_parser("inventory")
    inv.set_defaults(func=_cmd_audit_inventory)

    disc = sub.add_parser("discovery")
    disc_sub = disc.add_subparsers(dest="disc_cmd", required=True)
    cloud = disc_sub.add_parser("cloud")
    cloud.add_argument("--provider", default="aws")
    cloud.add_argument("--profile", default="dev")
    cloud.add_argument("--fixture", default=None)
    cloud.set_defaults(func=_cmd_discovery_cloud)
    directory = disc_sub.add_parser("dir")
    directory.add_argument("path")
    directory.set_defaults(func=_cmd_discovery_dir)

    classify = sub.add_parser("classify")
    classify.add_argument("path")
    classify.add_argument("--limit", type=int, default=100)
    classify.set_defaults(func=_cmd_classify)

    classify_pg = sub.add_parser("classify-postgres")
    classify_pg.add_argument("--table", required=True)
    classify_pg.set_defaults(func=_cmd_classify_postgres)

    risk = sub.add_parser("risk")
    risk_sub = risk.add_subparsers(dest="risk_cmd", required=True)
    score = risk_sub.add_parser("score")
    score.add_argument("--since", default="7d")
    score.add_argument("--fixture", default=None)
    score.set_defaults(func=_cmd_risk)

    access = sub.add_parser("access")
    access_sub = access.add_subparsers(dest="access_cmd", required=True)
    mapped = access_sub.add_parser("map")
    mapped.add_argument("--store", dest="store_id", default=None)
    mapped.add_argument("--fixture", default=None)
    mapped.set_defaults(func=_cmd_access)

    exposure = sub.add_parser("exposure")
    exposure_sub = exposure.add_subparsers(dest="exp_cmd", required=True)
    exp_scan = exposure_sub.add_parser("scan")
    exp_scan.add_argument("--provider", default="aws")
    exp_scan.add_argument("--fixture", default=None)
    exp_scan.set_defaults(func=_cmd_exposure)

    enc = sub.add_parser("encryption-check")
    enc.add_argument("path")
    enc.add_argument("--fixture", default=None)
    enc.set_defaults(func=_cmd_encryption)

    shadow = sub.add_parser("shadow")
    shadow_sub = shadow.add_subparsers(dest="shadow_cmd", required=True)
    sh_scan = shadow_sub.add_parser("scan")
    sh_scan.add_argument("--path", default=None)
    sh_scan.add_argument("--provider", default="aws")
    sh_scan.set_defaults(func=_cmd_shadow)

    custom = sub.add_parser("custom-types")
    custom_sub = custom.add_subparsers(dest="custom_cmd", required=True)
    custom_list = custom_sub.add_parser("list")
    custom_list.set_defaults(func=_cmd_custom_list)
    custom_test = custom_sub.add_parser("test")
    custom_test.add_argument("--type", required=True)
    custom_test.add_argument("--sample", required=True)
    custom_test.set_defaults(func=_cmd_custom_test)

    comp = sub.add_parser("compliance")
    comp_sub = comp.add_subparsers(dest="comp_cmd", required=True)
    mapped_c = comp_sub.add_parser("map")
    mapped_c.add_argument("--framework", default="gdpr")
    mapped_c.add_argument("--fixture", default=None)
    mapped_c.set_defaults(func=_cmd_compliance)

    ai = sub.add_parser("ai-security")
    ai_sub = ai.add_subparsers(dest="ai_cmd", required=True)
    ai_uri = ai_sub.add_parser("scan-vectorstore")
    ai_uri.add_argument("uri")
    ai_uri.set_defaults(func=_cmd_ai_uri)
    ai_ex = ai_sub.add_parser("scan-export")
    ai_ex.add_argument("path")
    ai_ex.set_defaults(func=_cmd_ai_export)

    rem = sub.add_parser("remediate")
    rem_sub = rem.add_subparsers(dest="rem_cmd", required=True)
    rem_plan = rem_sub.add_parser("plan")
    rem_plan.add_argument("--dry-run", action="store_true", default=True)
    rem_plan.set_defaults(func=_cmd_remediate_plan)
    rem_apply = rem_sub.add_parser("apply")
    rem_apply.add_argument("--policy", required=True)
    rem_apply.add_argument("--limit", type=int, default=5)
    rem_apply.add_argument("--apply", action="store_true")
    rem_apply.set_defaults(func=_cmd_remediate_apply)

    loop = sub.add_parser("loop")
    loop_sub = loop.add_subparsers(dest="loop_cmd", required=True)
    watch = loop_sub.add_parser("watch")
    watch.add_argument("--mode", choices=("community", "vendor", "all"), default="all")
    watch.add_argument("--fetch", action="store_true")
    watch.set_defaults(func=_cmd_loop_watch)
    monthly = loop_sub.add_parser("monthly")
    monthly.set_defaults(func=_cmd_loop_monthly)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(list(argv) if argv is not None else None)
    return int(ns.func(ns))


if __name__ == "__main__":
    raise SystemExit(main())
