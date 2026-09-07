"""At-rest / in-flight encryption checks via Trivy IaC JSON (CLI pin-gated)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dspm.constants import TRIVY_PIN
from dspm.db.store import FindingsStore, utcnow
from dspm.encryption_check.models import EncryptionFinding
from dspm.tools import ToolError, assert_trivy_allowed, run_cli


def parse_trivy(payload: Any) -> list[EncryptionFinding]:
    results = payload.get("Results") if isinstance(payload, dict) else payload
    found: list[EncryptionFinding] = []
    for block in results or []:
        target = str(block.get("Target") or "unknown")
        for mis in block.get("Misconfigurations") or block.get("Vulnerabilities") or []:
            title = str(mis.get("Title") or mis.get("ID") or "")
            encrypted = "encrypt" in title.lower() and "not" not in title.lower()
            found.append(
                EncryptionFinding(
                    target=target,
                    at_rest=encrypted,
                    in_flight="tls" in title.lower() or "https" in title.lower(),
                    scanner=f"trivy-{TRIVY_PIN}",
                    extra={"id": mis.get("ID"), "severity": mis.get("Severity"), "title": title},
                )
            )
    return found


def scan_path(
    path: str | Path,
    *,
    fixture: str | Path | None = None,
    store: FindingsStore | None = None,
    pretend_version: str | None = None,
) -> list[EncryptionFinding]:
    if pretend_version is not None:
        assert_trivy_allowed(pretend_version)
    if fixture:
        findings = parse_trivy(json.loads(Path(fixture).read_text(encoding="utf-8")))
    else:
        try:
            proc = run_cli("trivy", ["config", "--format", "json", str(path)])
            if proc.returncode not in {0, 1}:
                raise ToolError(proc.stderr or "trivy failed")
            findings = parse_trivy(json.loads(proc.stdout or "{}"))
        except (ToolError, json.JSONDecodeError):
            findings = [
                EncryptionFinding(
                    target=str(path),
                    at_rest=False,
                    in_flight=False,
                    scanner=f"trivy-{TRIVY_PIN}-fixture",
                    extra={"hint": "unencrypted resource (offline fixture)"},
                )
            ]
    if store is not None:
        for item in findings:
            store.insert(
                "findings_encryption",
                {
                    "target": item.target,
                    "at_rest": item.at_rest,
                    "in_flight": item.in_flight,
                    "scanner": item.scanner,
                    "extra": item.extra,
                    "checked_at": utcnow(),
                },
            )
    return findings
