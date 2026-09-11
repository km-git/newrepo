"""CLI shim for sspm.multi_tenant — delegates to the root app."""

from __future__ import annotations

from sspm.cli import main as root_main


def main(argv: list[str] | None = None) -> int:
    return root_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
