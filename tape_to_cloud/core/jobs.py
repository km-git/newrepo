"""SQLite-backed job queue for tape-to-cloud operations."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .constants import JOB_STATUSES, MODULES


class JobStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / "jobs.sqlite3"
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    module TEXT NOT NULL,
                    status TEXT NOT NULL,
                    params TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    layers_applied TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_job(self, module: str, params: dict[str, Any], *, layers: list[str] | None = None) -> dict[str, Any]:
        if module not in MODULES:
            raise ValueError(f"unknown module: {module}")
        now = datetime.now(UTC).isoformat()
        job_id = uuid4().hex
        row = {
            "id": job_id,
            "module": module,
            "status": "pending",
            "params": params,
            "result": None,
            "error": None,
            "layers_applied": layers or [],
            "created_at": now,
            "updated_at": now,
        }
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, module, status, params, result, error, layers_applied, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    module,
                    "pending",
                    json.dumps(params),
                    None,
                    None,
                    json.dumps(layers or []),
                    now,
                    now,
                ),
            )
            conn.commit()
        return row

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        layers_applied: list[str] | None = None,
    ) -> dict[str, Any] | None:
        if status and status not in JOB_STATUSES:
            raise ValueError(f"invalid status: {status}")
        job = self.get_job(job_id)
        if job is None:
            return None
        now = datetime.now(UTC).isoformat()
        if status:
            job["status"] = status
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        if layers_applied is not None:
            job["layers_applied"] = layers_applied
        job["updated_at"] = now
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs SET status=?, result=?, error=?, layers_applied=?, updated_at=?
                WHERE id=?
                """,
                (
                    job["status"],
                    json.dumps(job["result"]) if job["result"] is not None else None,
                    job["error"],
                    json.dumps(job["layers_applied"]),
                    now,
                    job_id,
                ),
            )
            conn.commit()
        return job

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_jobs(self, *, module: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM jobs"
        args: list[Any] = []
        if module:
            query += " WHERE module=?"
            args.append(module)
        query += " ORDER BY created_at DESC LIMIT ?"
        args.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, args).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            by_status = {
                r["status"]: r["cnt"]
                for r in conn.execute("SELECT status, COUNT(*) AS cnt FROM jobs GROUP BY status").fetchall()
            }
            by_module = {
                r["module"]: r["cnt"]
                for r in conn.execute("SELECT module, COUNT(*) AS cnt FROM jobs GROUP BY module").fetchall()
            }
        return {"total": total, "by_status": by_status, "by_module": by_module}

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "module": row["module"],
            "status": row["status"],
            "params": json.loads(row["params"]),
            "result": json.loads(row["result"]) if row["result"] else None,
            "error": row["error"],
            "layers_applied": json.loads(row["layers_applied"] or "[]"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
