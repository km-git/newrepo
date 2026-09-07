#!/usr/bin/env python3
"""Serve the EW browser monitor — static files + live /api/dashboard JSON."""

from __future__ import annotations

import argparse
import json
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
  explorer_launch_urls,
  publish_monetize,
  serve_monetize_http,
)
from engine.monitor_dashboard import build_dashboard_state, publish_monitor
from engine.tape_to_cloud_hub import serve_tape_to_cloud_http
from sspm.web.app import serve_sspm_http
from sspm.web.app import write_static as write_sspm_static


class MonitorHandler(SimpleHTTPRequestHandler):
  output_dir = "output"

  def __init__(self, *args, **kwargs):
    super().__init__(*args, directory=str(ROOT), **kwargs)

  def log_message(self, fmt: str, *args) -> None:
    if args and str(args[0]).startswith("GET /api/"):
      return
    super().log_message(fmt, *args)

  def do_GET(self) -> None:
    parsed = urlparse(self.path)
    if serve_tape_to_cloud_http(self, "GET", parsed.path, parse_qs(parsed.query)):
      return
    if parsed.path in ("/monitor", "/monitor/"):
      self.send_response(302)
      self.send_header("Location", "/output/monitor.html")
      self.end_headers()
      return
    if parsed.path == "/api/dashboard":
      self._serve_dashboard()
      return
    if serve_sspm_http(self, "GET", parsed.path, parse_qs(parsed.query), b""):
      return
    if serve_monetize_http(
      self,
      "GET",
      parsed.path,
      parse_qs(parsed.query),
      content_type=self.headers.get("Content-Type", ""),
    ):
      return
    super().do_GET()

  def do_POST(self) -> None:
    parsed = urlparse(self.path)
    length = int(self.headers.get("Content-Length") or 0)
    body = self.rfile.read(length) if length else b""
    if serve_sspm_http(self, "POST", parsed.path, parse_qs(parsed.query), body):
      return
    if serve_monetize_http(
      self,
      "POST",
      parsed.path,
      parse_qs(parsed.query),
      body,
      content_type=self.headers.get("Content-Type", ""),
    ):
      return
    self.send_error(404, "Not found")

  def _serve_dashboard(self) -> None:
    try:
      body = json.dumps(build_dashboard_state(self.output_dir), default=str).encode()
      self.send_response(200)
      self.send_header("Content-Type", "application/json")
      self.send_header("Cache-Control", "no-store")
      self.send_header("Content-Length", str(len(body)))
      self.end_headers()
      self.wfile.write(body)
    except OSError as e:
      err = json.dumps({"error": str(e)}).encode()
      self.send_response(500)
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile.write(err)


def run(
  host: str = DEFAULT_BIND_HOST,
  port: int = DEFAULT_BIND_PORT,
  output_dir: str = "output",
  publish: bool = True,
) -> None:
  if publish:
    paths = publish_monitor(output_dir)
    mpaths = publish_monetize(output_dir)
    print(f"[monitor] wrote {paths['monitor_html']}")
    print(f"[monitor] wrote {mpaths['monetize_html']}")
    try:
      spaths = write_sspm_static("reports")
      print(f"[monitor] wrote {spaths['html']}")
    except Exception as exc:
      print(f"[monitor] SSPM static skipped: {exc}")

  MonitorHandler.output_dir = output_dir
  server = ThreadingHTTPServer((host, port), MonitorHandler)
  print("[monitor] Tape-to-Cloud hub (default /):")
  print()
  for url in explorer_launch_urls(host, port, "/"):
    print(url)
    print()
  print("[monitor] Tape-to-Cloud reports:")
  print()
  for url in explorer_launch_urls(host, port, "/tape-to-cloud/reports"):
    print(url)
    print()
  print(f"[monitor] Tape-to-Cloud API: http://127.0.0.1:{port}/api/tape-to-cloud/status")
  print(f"[monitor] Tape-to-Cloud reports: http://127.0.0.1:{port}/tape-to-cloud/reports")
  print(f"[monitor] Tape-to-Cloud validation: http://127.0.0.1:{port}/tape-to-cloud/validation")
  print("[monitor] SSPM Explorer:")
  print()
  for url in explorer_launch_urls(host, port, "/sspm"):
    print(url)
    print()
  print(f"[monitor] SSPM API: http://127.0.0.1:{port}/api/sspm")
  print(f"[monitor] Bound to {host}:{port}")
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\n[monitor] stopped")
    server.shutdown()


def main() -> None:
  p = argparse.ArgumentParser(description="Serve EW browser monitor")
  p.add_argument("--port", type=int, default=DEFAULT_BIND_PORT)
  p.add_argument("--host", default=DEFAULT_BIND_HOST)
  p.add_argument("--output-dir", default="output")
  p.add_argument("--no-publish", action="store_true", help="Skip writing monitor.html on start")
  args = p.parse_args()
  run(args.host, args.port, args.output_dir, publish=not args.no_publish)


if __name__ == "__main__":
  main()
