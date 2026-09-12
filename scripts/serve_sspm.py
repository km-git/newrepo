#!/usr/bin/env python3
"""Serve the SSPM Configuration & Inventory Explorer (stdlib http.server)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sspm.web.app import DEFAULT_HOST, DEFAULT_PORT, run, write_static


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve SSPM Explorer")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args()
    if args.static:
        paths = write_static("reports")
        print(f"file://{Path(paths['html']).resolve()}")
        print(f"[sspm-ui] wrote {paths['html']}")
        return
    run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
