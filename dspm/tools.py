"""Subprocess wrappers and supply-chain gates for CLI-only OSS tools."""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from dspm.constants import CLI_TOOLS, TRIVY_MALICIOUS, TRIVY_MIN, TRIVY_PIN

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


class ToolError(RuntimeError):
    """A required CLI tool is missing, blocked, or returned a bad status."""


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.search(text or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def format_version(ver: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in ver)


def assert_trivy_allowed(version_text: str) -> str:
    """Refuse Trivy versions in the CVE-2026-33634 malicious window.

    Allowed: ``v0.70+`` (pin ``0.71.2``). Forbidden: ``0.69.4`` / ``0.69.5`` / ``0.69.6``
    and anything older than ``0.70.0``.
    """
    raw = (version_text or "").strip().lstrip("v")
    for bad in TRIVY_MALICIOUS:
        if raw.startswith(bad):
            raise ToolError(
                f"refusing Trivy {bad}: CVE-2026-33634 supply-chain incident 2026-03-19. Install {TRIVY_PIN} or v0.70+."
            )
    parsed = parse_version(raw)
    if parsed is None:
        raise ToolError(f"cannot parse Trivy version from {version_text!r}; pin {TRIVY_PIN}")
    if parsed < TRIVY_MIN:
        raise ToolError(
            f"refusing Trivy {format_version(parsed)}: minimum allowed is {format_version(TRIVY_MIN)} "
            f"(CVE-2026-33634). Pin {TRIVY_PIN}."
        )
    return format_version(parsed)


def which(binary: str) -> str | None:
    if binary not in CLI_TOOLS and binary != "c7n-org":
        raise ToolError(f"refusing to execute unlisted binary {binary!r}")
    found = shutil.which(binary)
    return found


def run_cli(
    binary: str,
    args: Sequence[str],
    *,
    cwd: str | Path | None = None,
    timeout: int = 120,
    check_trivy: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run an allow-listed CLI. Steampipe is never imported as a library (AGPL-3.0)."""
    path = which(binary)
    if path is None:
        raise ToolError(f"{binary} is not installed on PATH (CLI subprocess only)")
    if binary == "trivy" and check_trivy:
        probe = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert_trivy_allowed((probe.stdout or "") + (probe.stderr or ""))
    cmd = [path, *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
        check=False,
    )
