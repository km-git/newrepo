"""List live ingest jobs from the local store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tape_to_cloud.ids import JOB_ID_RE, resolved_job_dir
from tape_to_cloud.store import default_store


def list_jobs(store: Path | None = None) -> list[dict[str, Any]]:
    root = (store or default_store()) / "jobs"
    if not root.is_dir():
        return []
    jobs: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/report.json"), reverse=True):
        job_id = path.parent.name
        if not JOB_ID_RE.fullmatch(job_id):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("id") != job_id:
            continue
        jobs.append(
            {
                "id": job_id,
                "kind": data.get("kind"),
                "sample": bool(data.get("sample", False)),
                "title": data.get("title"),
                "status": data.get("status"),
                "matter_id": data.get("matter_id"),
                "object_count": data.get("object_count"),
                "bytes": data.get("bytes"),
                "canonical_sha256": data.get("canonical_sha256"),
                "href": f"/tape-to-cloud/jobs/{job_id}",
                "api": f"/api/tape-to-cloud/jobs/{job_id}",
            }
        )
    return jobs


def load_job(job_id: str, store: Path | None = None) -> dict[str, Any] | None:
    try:
        path = resolved_job_dir(store or default_store(), job_id) / "report.json"
    except ValueError:
        return None
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
