"""Strict identifiers so job/object paths cannot escape the store."""

from __future__ import annotations

import os
import re
from pathlib import Path

JOB_ID_RE = re.compile(r"^job-(?P<stamp>[0-9]{8}T[0-9]{6}Z)-(?P<hex>[0-9a-f]{8})$")


def parse_job_id(job_id: str) -> str:
    match = JOB_ID_RE.fullmatch((job_id or "").strip())
    if match is None:
        raise ValueError(f"invalid job id: {job_id!r}")
    return "job-" + match.group("stamp") + "-" + match.group("hex")


def resolved_job_dir(store: Path, job_id: str) -> Path:
    safe_id = parse_job_id(job_id)
    jobs_root = os.path.realpath(os.path.join(os.path.realpath(str(store)), "jobs"))
    candidate = os.path.realpath(os.path.join(jobs_root, safe_id))
    prefix = jobs_root + os.sep
    if not candidate.startswith(prefix):
        raise ValueError(f"job path escapes store: {job_id!r}")
    return Path(candidate)
