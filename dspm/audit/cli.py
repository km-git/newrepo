"""Typer-compatible argparse entry for dspm.audit (delegates to dspm.cli)."""

from __future__ import annotations

from dspm.cli import main as root_main


def main(argv=None) -> int:
    return root_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
