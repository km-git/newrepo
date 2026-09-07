"""Mondoo cnspec CLI subprocess. Never imported as a library."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from sspm.constants import CNSPEC_PIN

PROVIDERS = {
    "m365": ("ms365",),
    "gws": ("google-workspace",),
    "github": ("github", "org"),
    "slack": ("slack",),
    "okta": ("okta",),
}


def which_cnspec() -> str | None:
    return shutil.which("cnspec")


def scan(
    tenant_type: str,
    *,
    extra_args: list[str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Run `cnspec scan <provider>` and parse JSON. Returns a skip payload if missing."""
    binary = which_cnspec()
    if not binary:
        return {
            "ok": False,
            "scanner": "cnspec",
            "version_pin": CNSPEC_PIN,
            "reason": "cnspec not on PATH; using fixture/API fallback",
        }
    provider = list(PROVIDERS.get(tenant_type, (tenant_type,)))
    cmd = [binary, "scan", *provider, "--output", "json", *(extra_args or [])]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "scanner": "cnspec", "reason": str(exc), "cmd": cmd}
    payload: Any
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {"raw": (proc.stdout or "")[:4000]}
    return {
        "ok": proc.returncode == 0,
        "scanner": "cnspec",
        "version_pin": CNSPEC_PIN,
        "returncode": proc.returncode,
        "payload": payload,
        "stderr": (proc.stderr or "")[:1000],
    }


def policy_dir() -> Path:
    return Path(__file__).resolve().parent / "cnspec-policies"
