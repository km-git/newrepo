"""SQLite finding store. Postgres is optional when COST_DATABASE_URL is set."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cost.paths import SCHEMA_PATH, db_path, ensure_output
from cost.settings import database_url

TABLES = (
    "findings_resources",
    "findings_costs",
    "findings_rightsizing",
    "findings_untagged",
    "findings_drift",
    "findings_compliance",
    "tenants",
)


def _utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def connect(path: Path | None = None) -> sqlite3.Connection:
    ensure_output()
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    own = conn is None
    conn = conn or connect()
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    if own:
        return conn
    return conn


def upsert_tenant(conn: sqlite3.Connection, tenant_id: str, name: str, provider: str) -> None:
    conn.execute(
        """
        INSERT INTO tenants (id, name, provider, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET name = excluded.name, provider = excluded.provider
        """,
        (tenant_id, name, provider, _utcnow()),
    )


def replace_rows(conn: sqlite3.Connection, table: str, rows: Iterable[dict[str, Any]]) -> int:
    if table not in TABLES:
        raise ValueError(f"unknown table {table}")
    payload = list(rows)
    if not payload:
        return 0
    columns = list(payload[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    colsql = ", ".join(columns)
    tenant = payload[0].get("tenant_id")
    providers = {row.get("provider") for row in payload if row.get("provider")}
    if len(providers) == 1 and "provider" in columns:
        conn.execute(
            f"DELETE FROM {table} WHERE tenant_id = ? AND provider = ?",
            (tenant, payload[0].get("provider")),
        )
    else:
        conn.execute(
            f"DELETE FROM {table} WHERE tenant_id = ?",
            (tenant,),
        )
    conn.executemany(
        f"INSERT INTO {table} ({colsql}) VALUES ({placeholders})",
        [tuple(row.get(c) for c in columns) for row in payload],
    )
    conn.commit()
    return len(payload)


def fetch_all(conn: sqlite3.Connection, table: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
    if table not in TABLES:
        raise ValueError(f"unknown table {table}")
    if tenant_id:
        cur = conn.execute(
            f"SELECT * FROM {table} WHERE tenant_id = ?",
            (tenant_id,),
        )
    else:
        cur = conn.execute(f"SELECT * FROM {table}")
    return [dict(r) for r in cur.fetchall()]


def dumps(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def using_postgres() -> bool:
    return database_url().startswith("postgres")
