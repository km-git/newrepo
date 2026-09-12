"""CLI subprocess helpers — Steampipe/Prowler/Trivy never imported as libraries."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from cost.constants import TRIVY_MALICIOUS, TRIVY_PIN


def which(name: str) -> str | None:
    return shutil.which(name)


def assert_trivy_allowed(version_output: str) -> str:
    match = re.search(r"(\d+\.\d+\.\d+)", version_output)
    if not match:
        raise RuntimeError(f"Cannot parse Trivy version from: {version_output!r}")
    ver = match.group(1)
    if ver in TRIVY_MALICIOUS or ver.startswith("0.69."):
        raise RuntimeError(f"Refusing Trivy {ver} (CVE-2026-33634 window)")
    major, minor, _ = (int(x) for x in ver.split("."))
    if major == 0 and minor == 69:
        raise RuntimeError(f"Refusing Trivy {ver} (CVE-2026-33634 window)")
    return ver


def run_steampipe_query(query: str, *, fixture: Path | None = None) -> list[dict[str, Any]]:
    """Run Steampipe as CLI subprocess (AGPL — never import steampipe)."""
    if fixture and fixture.exists():
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        return list(payload.get("rows", payload if isinstance(payload, list) else []))
    if not which("steampipe"):
        raise FileNotFoundError("steampipe not on PATH; pass --fixture for offline runs")
    proc = subprocess.run(
        ["steampipe", "query", query, "--output", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "steampipe query failed")
    data = json.loads(proc.stdout or "[]")
    if isinstance(data, dict) and "rows" in data:
        return list(data["rows"])
    return list(data) if isinstance(data, list) else []


def run_prowler(*, provider: str, out_dir: Path, fixture: Path | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if fixture and fixture.exists():
        target = out_dir / "prowler-output.json"
        target.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
        return target
    if not which("prowler"):
        raise FileNotFoundError("prowler not on PATH; pass --fixture for offline runs")
    subprocess.run(
        ["prowler", provider, "--output-formats", "json", "-o", str(out_dir)],
        check=True,
    )
    matches = list(out_dir.glob("*.json"))
    if not matches:
        raise RuntimeError("prowler produced no JSON output")
    return matches[0]


def trivy_version_ok() -> bool:
    if not which("trivy"):
        return False
    try:
        out = subprocess.check_output(["trivy", "--version"], text=True)
        assert_trivy_allowed(out)
        return True
    except (RuntimeError, subprocess.CalledProcessError):
        return False


def recommended_trivy_pin() -> str:
    return f"v{TRIVY_PIN}"
