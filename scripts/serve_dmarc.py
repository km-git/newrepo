#!/usr/bin/env python3
"""Serve the DMARC deliverability explorer (stdlib http.server)."""

from __future__ import annotations

import argparse
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dmarc.webui import (  # noqa: E402
    DEFAULT_BIND_HOST,
    DEFAULT_BIND_PORT,
    print_explorer_launch,
    publish_static,
    serve_dmarc_http,
)


class DmarcHandler(SimpleHTTPRequestHandler):
    output_dir = "output/dmarc"

    def log_message(self, fmt: str, *args: object) -> None:
        if args and str(args[0]).startswith("GET /api/"):
            return
        super().log_message(fmt, *args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if serve_dmarc_http(self, "GET", parsed.path, parse_qs(parsed.query), root_is_dmarc=True):
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
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


def run(host: str = DEFAULT_BIND_HOST, port: int = DEFAULT_BIND_PORT, output_dir: str = "output/dmarc") -> None:
    DmarcHandler.output_dir = output_dir
    server = ThreadingHTTPServer((host, port), DmarcHandler)
    print_explorer_launch(host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[dmarc-ui] stopped")
        server.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve DMARC deliverability explorer")
    parser.add_argument("--port", type=int, default=DEFAULT_BIND_PORT)
    parser.add_argument("--host", default=DEFAULT_BIND_HOST)
    parser.add_argument("--output-dir", default="output/dmarc")
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args()
    if args.static:
        print(publish_static(Path(args.output_dir)))
        return
    run(args.host, args.port, args.output_dir)


if __name__ == "__main__":
    main()
