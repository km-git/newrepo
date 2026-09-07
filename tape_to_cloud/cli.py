"""Tape-to-cloud CLI: live ingest plus sample reports.

Usage:
  python -m tape_to_cloud ingest SOURCE --matter MATTER [--worm-until ISO] [--keyword TEXT]
  python -m tape_to_cloud restore JOB_ID DEST
  python -m tape_to_cloud verify JOB_ID
  python -m tape_to_cloud status
  python -m tape_to_cloud report [module|job-pack]
  python -m tape_to_cloud list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tape_to_cloud.catalog import MODULES
from tape_to_cloud.ingest import default_store, ingest, restore_job, verify_job
from tape_to_cloud.jobs import list_jobs
from tape_to_cloud.sample_reports import get_report, list_reports


def _print(obj: object) -> None:
    print(json.dumps(obj, indent=2, default=str, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tape_to_cloud")
    parser.add_argument(
        "--store", default=None, help="Store root (default EW_TAPE_STORE or output/tape_to_cloud/store)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_in = sub.add_parser("ingest", help="Ingest a file or directory (real SHA-256 copy)")
    p_in.add_argument("source")
    p_in.add_argument("--matter", default="UNTITLED")
    p_in.add_argument("--keyword", default=None)
    p_in.add_argument("--worm-until", default=None, help="ISO-8601 retention lock expiry")
    p_in.add_argument("--unwrap-key", default=None, help="Required to accept .enc files (still stored opaque)")

    p_rs = sub.add_parser("restore", help="Restore job objects to a directory")
    p_rs.add_argument("job_id")
    p_rs.add_argument("dest")

    p_vf = sub.add_parser("verify", help="Re-hash stored objects against the job report")
    p_vf.add_argument("job_id")

    sub.add_parser("status", help="List live jobs")

    report = sub.add_parser("report", help="Print a sample module or job-pack report as JSON")
    report.add_argument("module", nargs="?", default="job-pack", help="module id or job-pack (default job-pack)")
    listing = sub.add_parser("list", help="List sample reports")
    listing.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "list":
        rows = list_reports()
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                print(f"{row['module']:16} {row['report_id']}  {row['href']}")
        return 0
    if args.cmd == "report":
        try:
            payload = get_report(args.module)
        except KeyError:
            print(f"unknown module: {args.module}", file=sys.stderr)
            print("known:", ", ".join((*MODULES, "job-pack")), file=sys.stderr)
            return 2
        print(json.dumps(payload, indent=2, default=str))
        return 0

    store = Path(args.store).resolve() if args.store else default_store()
    if args.cmd == "ingest":
        payload = ingest(
            Path(args.source),
            store=store,
            matter_id=args.matter,
            keyword=args.keyword,
            worm_until=args.worm_until,
            unwrap_key=Path(args.unwrap_key) if args.unwrap_key else None,
        )
        _print(payload)
        return 0 if payload.get("object_count") else 2
    if args.cmd == "restore":
        try:
            _print(restore_job(args.job_id, Path(args.dest), store=store))
        except (ValueError, FileNotFoundError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        return 0
    if args.cmd == "verify":
        try:
            result = verify_job(args.job_id, store=store)
        except (ValueError, FileNotFoundError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        _print(result)
        return 0 if result["objects_ok"] and result["report_hash_ok"] else 2
    if args.cmd == "status":
        _print({"store": str(store), "jobs": list_jobs(store)})
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
