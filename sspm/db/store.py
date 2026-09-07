"""File-backed SQLite store so tests and CLI runs do not need Docker/Postgres."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def default_db_path() -> Path:
    override = os.environ.get("SSPM_DB")
    if override:
        return Path(override)
    return Path("output/sspm/sspm.sqlite")


def utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def _adapt(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if isinstance(value, bool):
        return int(value)
    return value


class FindingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_db_path()
        self.conn = connect(self.path)

    def insert(self, table: str, row: dict[str, Any]) -> int:
        payload = {k: _adapt(v) for k, v in row.items()}
        cols = ", ".join(payload)
        placeholders = ", ".join("?" for _ in payload)
        cur = self.conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            tuple(payload.values()),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def fetchall(self, table: str, where: str | None = None, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        rows = self.conn.execute(sql, params).fetchall()
        self.conn.commit()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
