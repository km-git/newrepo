"""List live ingest jobs from the local store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tape_to_cloud.ingest import default_store


def list_jobs(store: Path | None = None) -> list[dict[str, Any]]:
    root = (store or default_store()) / "jobs"
    if not root.is_dir():
        return []
    jobs: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/report.json"), reverse=True):
        data = json.loads(path.read_text(encoding="utf-8"))
        jobs.append(
            {
                "id": data.get("id"),
                "kind": data.get("kind"),
                "sample": bool(data.get("sample", False)),
                "title": data.get("title"),
                "status": data.get("status"),
                "matter_id": data.get("matter_id"),
                "object_count": data.get("object_count"),
                "bytes": data.get("bytes"),
                "canonical_sha256": data.get("canonical_sha256"),
                "href": f"/tape-to-cloud/jobs/{data.get('id')}",
                "api": f"/api/tape-to-cloud/jobs/{data.get('id')}",
            }
        )
    return jobs


def load_job(job_id: str, store: Path | None = None) -> dict[str, Any] | None:
    path = (store or default_store()) / "jobs" / job_id / "report.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
