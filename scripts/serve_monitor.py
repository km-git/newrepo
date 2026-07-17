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

from engine.monitor_dashboard import build_dashboard_state, publish_monitor


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
    if parsed.path in ("/", "/monitor", "/monitor/"):
      self.send_response(302)
      self.send_header("Location", "/output/monitor.html")
      self.end_headers()
      return
    if parsed.path == "/api/dashboard":
      self._serve_dashboard()
      return
    super().do_GET()

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


def run(host: str = "127.0.0.1", port: int = 8765, output_dir: str = "output", publish: bool = True) -> None:
  if publish:
    paths = publish_monitor(output_dir)
    print(f"[monitor] wrote {paths['monitor_html']}")

  MonitorHandler.output_dir = output_dir
  server = ThreadingHTTPServer((host, port), MonitorHandler)
  url = f"http://{host}:{port}/"
  print(f"[monitor] Open {url}")
  print(f"[monitor] Dashboard API: http://{host}:{port}/api/dashboard")
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\n[monitor] stopped")
    server.shutdown()


def main() -> None:
  p = argparse.ArgumentParser(description="Serve EW browser monitor")
  p.add_argument("--port", type=int, default=8765)
  p.add_argument("--host", default="127.0.0.1")
  p.add_argument("--output-dir", default="output")
  p.add_argument("--no-publish", action="store_true", help="Skip writing monitor.html on start")
  args = p.parse_args()
  run(args.host, args.port, args.output_dir, publish=not args.no_publish)


if __name__ == "__main__":
  main()
