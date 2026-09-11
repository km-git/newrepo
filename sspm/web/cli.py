"""Web CLI shim."""

from __future__ import annotations

from sspm.cli import main as root_main


def main(argv: list[str] | None = None) -> int:
    return root_main(argv or ["web"])
