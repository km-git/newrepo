"""Strict identifiers so job/object paths cannot escape the store."""

from __future__ import annotations

import re
from pathlib import Path

JOB_ID_RE = re.compile(r"^job-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")


def parse_job_id(job_id: str) -> str:
    value = (job_id or "").strip()
    if not JOB_ID_RE.fullmatch(value):
        raise ValueError(f"invalid job id: {job_id!r}")
    return value


def resolved_job_dir(store: Path, job_id: str) -> Path:
    jobs_root = store.resolve() / "jobs"
    path = (jobs_root / parse_job_id(job_id)).resolve()
    path.relative_to(jobs_root)
    return path
