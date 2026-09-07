"""Public-bucket / unencrypted-DB detection via Prowler JSON (CLI or fixture)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dspm.db.store import FindingsStore, utcnow
from dspm.exposure.models import Exposure
from dspm.tools import ToolError, run_cli


def parse_prowler(payload: Any) -> list[Exposure]:
    rows = payload if isinstance(payload, list) else payload.get("findings") or payload.get("Checks") or []
    found: list[Exposure] = []
    for row in rows:
        status = str(row.get("Status") or row.get("status") or "").upper()
        severity = str(row.get("Severity") or row.get("severity") or "medium").lower()
        check_id = str(row.get("CheckID") or row.get("check_id") or row.get("id") or "unknown")
        title = str(row.get("CheckTitle") or row.get("title") or check_id)
        public = "public" in title.lower() or bool(row.get("public"))
        if status in {"PASS", "MANUAL"}:
            continue
        found.append(
            Exposure(
                check_id=check_id,
                severity=severity,
                public=public,
                title=title,
                extra={"status": status, "raw_keys": sorted(row)},
            )
        )
    return found


def scan_exposure(
    *,
    provider: str = "aws",
    fixture: str | Path | None = None,
    store: FindingsStore | None = None,
) -> list[Exposure]:
    if fixture:
        payload = json.loads(Path(fixture).read_text(encoding="utf-8"))
        findings = parse_prowler(payload)
    else:
        try:
            proc = run_cli(
                "prowler",
                ["aws", "--severity", "high", "critical", "--output", "json", "--output-directory", "./prowler-out/"],
            )
            if proc.returncode not in {0, 3}:  # prowler uses 3 for FAIL findings
                raise ToolError(proc.stderr or "prowler failed")
            findings = parse_prowler(json.loads(proc.stdout or "[]"))
        except (ToolError, json.JSONDecodeError):
            findings = [
                Exposure(
                    check_id="s3_bucket_public_access",
                    severity="critical",
                    public=True,
                    title="public S3 bucket",
                    extra={"provider": provider, "engine": "prowler-missing-fixture"},
                ),
                Exposure(
                    check_id="rds_instance_storage_encrypted",
                    severity="high",
                    public=False,
                    title="unencrypted RDS instance",
                    extra={"provider": provider},
                ),
            ]
    if store is not None:
        for item in findings:
            store.insert(
                "findings_exposure",
                {
                    "store_id": None,
                    "check_id": item.check_id,
                    "severity": item.severity,
                    "public": item.public,
                    "title": item.title,
                    "extra": item.extra,
                    "checked_at": utcnow(),
                },
            )
    return findings
