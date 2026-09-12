"""Subprocess wrappers for external OSS CLI tools (Steampipe, Trivy, Prowler, CloudQuery)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class CliToolError(RuntimeError):
    pass


def which(tool: str) -> str | None:
    return shutil.which(tool)


def run_cli(
    cmd: list[str],
    *,
    timeout: int = 120,
    fixture_path: Path | None = None,
) -> dict[str, Any] | list[Any]:
    """Run a CLI tool or return fixture data when unavailable."""
    if fixture_path and fixture_path.exists():
        return json.loads(fixture_path.read_text(encoding="utf-8"))
    if not which(cmd[0]):
        if fixture_path:
            raise CliToolError(f"{cmd[0]} not installed and no fixture at {fixture_path}")
        return []
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise CliToolError(result.stderr or result.stdout or f"{cmd[0]} failed")
    stdout = result.stdout.strip()
    if not stdout:
        return []
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw": stdout}
