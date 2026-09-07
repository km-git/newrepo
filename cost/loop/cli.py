"""Typer-compatible argparse entry for cost.loop (delegates to cost.cli)."""

from __future__ import annotations

from cost.cli import main as root_main


def main(argv=None) -> int:
    return root_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
