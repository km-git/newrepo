"""dmarc CLI — argparse, Typer-compatible ``app`` entry."""

from __future__ import annotations

import argparse
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dmarc.aggregate_report import cli as aggregate_cli
from dmarc.audit import cli as audit_cli
from dmarc.dkim_check import cli as dkim_cli
from dmarc.dmarc_ingest import cli as ingest_cli
from dmarc.dns_check import cli as dns_cli
from dmarc.forensic_report import cli as forensic_cli
from dmarc.inbox_placement import cli as inbox_cli
from dmarc.loop.monthly import write_monthly
from dmarc.report_writer import cli as report_cli
from dmarc.spf_parser import cli as spf_cli
from dmarc.webui import DEFAULT_BIND_HOST, DEFAULT_BIND_PORT, print_explorer_launch, publish_static, serve_dmarc_http


def _add_ui(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("ui", help="Stdlib web dashboard (also: ew_tool.py --dmarc-ui)")
    parser.add_argument("--host", default=DEFAULT_BIND_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_BIND_PORT)
    parser.add_argument("--static", action="store_true")
    parser.add_argument("--output-dir", default="output/dmarc")
    parser.set_defaults(handler=cmd_ui)


def cmd_ui(args: argparse.Namespace) -> int:
    if args.static:
        paths = publish_static(Path(args.output_dir))
        print(json.dumps(paths, indent=2))
        print(f"file://{Path(paths['static']).resolve()}")
        return 0

    class Handler(SimpleHTTPRequestHandler):
        output_dir = args.output_dir

        def log_message(self, fmt: str, *log_args: object) -> None:
            if log_args and str(log_args[0]).startswith("GET /api/"):
                return
            super().log_message(fmt, *log_args)

        def do_GET(self) -> None:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(self.path)
            if serve_dmarc_http(self, "GET", parsed.path, parse_qs(parsed.query), root_is_dmarc=True):
                return
            self.send_error(404, "Not found")

        def do_POST(self) -> None:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            if serve_dmarc_http(
                self,
                "POST",
                parsed.path,
                parse_qs(parsed.query),
                body,
                content_type=self.headers.get("Content-Type", ""),
                root_is_dmarc=True,
            ):
                return
            self.send_error(404, "Not found")

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print_explorer_launch(args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


def _add_monthly(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("monthly", help="Write monthly/YYYY-MM.md + deliverability-trend.md")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--monthly-dir", default="monthly")
    parser.set_defaults(handler=cmd_monthly)


def cmd_monthly(args: argparse.Namespace) -> int:
    paths = write_monthly(
        root=Path(args.output_dir) if args.output_dir else None,
        monthly_dir=Path(args.monthly_dir),
    )
    print(json.dumps(paths, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dmarc",
        description="Email Deliverability & Brand-Protection Review toolkit (read-only).",
    )
    sub = parser.add_subparsers(dest="group", required=True)
    audit_cli.add_parser(sub)
    dns_cli.add_parser(sub)
    spf_cli.add_parser(sub)
    dkim_cli.add_parser(sub)
    ingest_cli.add_parser(sub)
    aggregate_cli.add_parser(sub)
    forensic_cli.add_parser(sub)
    inbox_cli.add_parser(sub)
    report_cli.add_parser(sub)
    _add_ui(sub)
    _add_monthly(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    return int(handler(args))


def app() -> None:
    """Console-script entry (`dmarc = dmarc.cli:app`)."""
    raise SystemExit(main())


if __name__ == "__main__":
    sys.exit(main())
