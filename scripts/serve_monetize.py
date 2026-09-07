#!/usr/bin/env python3
"""Serve the Monetize Explorer — static HTML + /api/monetize JSON (stdlib http.server)."""

from __future__ import annotations

import argparse
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from engine.monetize_ui import (
  DEFAULT_BIND_HOST,
  DEFAULT_BIND_PORT,
  print_explorer_launch,
  print_static_launch,
  publish_monetize,
  publish_static_monetize,
  serve_monetize_http,
)


class MonetizeHandler(SimpleHTTPRequestHandler):
  output_dir = "output"
  root_is_monetize = True

  def __init__(self, *args, **kwargs):
    super().__init__(*args, directory=str(ROOT), **kwargs)

  def log_message(self, fmt: str, *args) -> None:
    if args and str(args[0]).startswith("GET /api/"):
      return
    super().log_message(fmt, *args)

  def do_GET(self) -> None:
    parsed = urlparse(self.path)
    if parsed.path in ("/", "/monetize", "/monetize/"):
      if serve_monetize_http(
        self,
        "GET",
        "/monetize",
        parse_qs(parsed.query),
        root_is_monetize=True,
      ):
        return
    if serve_monetize_http(
      self,
      "GET",
      parsed.path,
      parse_qs(parsed.query),
      content_type=self.headers.get("Content-Type", ""),
      root_is_monetize=self.root_is_monetize,
    ):
      return
    if parsed.path in ("/monitor", "/monitor/"):
      self.send_response(302)
      self.send_header("Location", "/output/monitor.html")
      self.end_headers()
      return
    super().do_GET()

  def do_POST(self) -> None:
    parsed = urlparse(self.path)
    length = int(self.headers.get("Content-Length") or 0)
    body = self.rfile.read(length) if length else b""
    if serve_monetize_http(
      self,
      "POST",
      parsed.path,
      parse_qs(parsed.query),
      body,
      content_type=self.headers.get("Content-Type", ""),
      root_is_monetize=self.root_is_monetize,
    ):
      return
    self.send_error(404, "Not found")


def run(
  host: str = DEFAULT_BIND_HOST,
  port: int = DEFAULT_BIND_PORT,
  output_dir: str = "output",
  publish: bool = True,
) -> None:
  if publish:
    paths = publish_monetize(output_dir)
    print(f"[monetize-ui] wrote {paths['monetize_html']}")

  MonetizeHandler.output_dir = output_dir
  server = ThreadingHTTPServer((host, port), MonetizeHandler)
  print_explorer_launch(host, port)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\n[monetize-ui] stopped")
    server.shutdown()


def write_static(output_dir: str = "output") -> dict:
  paths = publish_static_monetize(output_dir)
  print_static_launch(paths)
  return paths


def main() -> None:
  p = argparse.ArgumentParser(description="Serve Monetize Explorer")
  p.add_argument("--port", type=int, default=DEFAULT_BIND_PORT)
  p.add_argument("--host", default=DEFAULT_BIND_HOST)
  p.add_argument("--output-dir", default="output")
  p.add_argument("--no-publish", action="store_true", help="Skip writing monetize.html on start")
  p.add_argument(
    "--static",
    action="store_true",
    help="Write self-contained HTML (file://) and exit — no server",
  )
  args = p.parse_args()
  if args.static:
    write_static(args.output_dir)
    return
  run(args.host, args.port, args.output_dir, publish=not args.no_publish)


if __name__ == "__main__":
  main()
