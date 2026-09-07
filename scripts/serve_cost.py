#!/usr/bin/env python3
"""Serve the Cost & Configuration Review UI (stdlib http.server)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cost.webui.server import run_ui, write_static_html  # noqa: E402


def write_static(output_dir: str = "output") -> None:
    from pathlib import Path as P

    live = P(output_dir) / "cost.html"
    live.parent.mkdir(parents=True, exist_ok=True)
    html = write_static_html()
    live.write_text(html.read_text(encoding="utf-8") if html.exists() else "", encoding="utf-8")
    if html.exists():
        live.write_text(html.read_text(encoding="utf-8"), encoding="utf-8")
    print(html.resolve().as_uri())
    print(str(html.resolve()))


def main() -> None:
    p = argparse.ArgumentParser(description="Serve Cloud Cost & Configuration Review UI")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--static", action="store_true")
    args = p.parse_args()
    run_ui(host=args.host, port=args.port, static=args.static, sandbox=True)


if __name__ == "__main__":
    main()
