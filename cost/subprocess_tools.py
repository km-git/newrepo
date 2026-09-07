"""Invoke third-party CLIs as subprocesses. Never import Steampipe (AGPL-3.0)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

ALLOWED_BINARIES = frozenset(
    {
        "steampipe",
        "prowler",
        "trivy",
        "custodian",
        "c7n-org",
        "pip-audit",
        "python",
        "python3",
    }
)


class CliUnavailable(RuntimeError):
    """Binary is not on PATH — callers fall back to sandbox fixtures."""


def which(binary: str) -> str | None:
    if binary not in ALLOWED_BINARIES:
        raise ValueError(f"refusing to look up unlisted binary: {binary}")
    return shutil.which(binary)


def run_cli(
    binary: str,
    args: list[str],
    *,
    cwd: str | Path | None = None,
    timeout: int = 120,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run an allow-listed CLI. Args are a list — never shell=True."""
    path = which(binary)
    if path is None:
        raise CliUnavailable(binary)
    cmd = [path, *args]
    return subprocess.run(  # noqa: S603 — allow-listed binary, argv list, no shell
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )


def steampipe_query(sql: str, timeout: int = 120) -> list[dict[str, Any]]:
    """`steampipe query --output json`. Never `import steampipe`."""
    proc = run_cli("steampipe", ["query", sql, "--output", "json"], timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "steampipe failed")
    payload = json.loads(proc.stdout or "[]")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        rows = payload.get("rows") or payload.get("result") or []
        return list(rows) if isinstance(rows, list) else []
    return []


def prowler_snapshot(provider: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    proc = run_cli(
        "prowler",
        [provider, "--output", "json", "--output-directory", str(output_dir)],
        timeout=300,
    )
    if proc.returncode not in {0, 3}:  # prowler uses 3 for findings
        raise RuntimeError(proc.stderr.strip() or "prowler failed")
    files = sorted(output_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no prowler JSON under {output_dir}")
    return files[-1]


def trivy_version() -> str | None:
    path = which("trivy")
    if path is None:
        return None
    proc = run_cli("trivy", ["--version"], timeout=15)
    first = (proc.stdout or proc.stderr or "").splitlines()[0] if proc.stdout or proc.stderr else ""
    return first.strip() or None
