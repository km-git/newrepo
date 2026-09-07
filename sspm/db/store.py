"""SQLite/Postgres findings store."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB = ROOT / "output" / "sspm" / "sspm.sqlite"


def _utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


ALLOWED_TABLES = frozenset(
    {
        "findings_tenants",
        "findings_settings",
        "findings_oauth",
        "findings_drift",
        "findings_compliance",
        "tenants",
    }
)


class FindingsStore:
    def __init__(self, path: Path | str | None = None) -> None:
        env = os.environ.get("SSPM_DB") or os.environ.get("DATABASE_URL")
        if path:
            self.path = Path(path)
        elif env and env.startswith("postgres"):
            self.path = None
            self._pg_url = env
        else:
            self.path = DEFAULT_DB
            self._pg_url = None
        self._init()

    def _init(self) -> None:
        if self._pg_url:
            import psycopg

            with psycopg.connect(self._pg_url) as conn:
                conn.execute(SCHEMA.read_text())
                conn.commit()
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._sqlite() as conn:
            conn.executescript(_sqlite_schema())
            conn.commit()

    @contextmanager
    def _sqlite(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        if self._pg_url:
            import psycopg

            with psycopg.connect(self._pg_url) as conn:
                conn.execute(sql, params)
                conn.commit()
            return
        with self._sqlite() as conn:
            conn.execute(sql, params)
            conn.commit()

    def fetchall(self, table: str, limit: int = 500) -> list[dict[str, Any]]:
        if table not in ALLOWED_TABLES:
            raise ValueError(f"unknown table: {table}")
        queries = {
            "findings_tenants": "SELECT * FROM findings_tenants ORDER BY id DESC LIMIT ?",
            "findings_settings": "SELECT * FROM findings_settings ORDER BY id DESC LIMIT ?",
            "findings_oauth": "SELECT * FROM findings_oauth ORDER BY id DESC LIMIT ?",
            "findings_drift": "SELECT * FROM findings_drift ORDER BY id DESC LIMIT ?",
            "findings_compliance": "SELECT * FROM findings_compliance ORDER BY id DESC LIMIT ?",
            "tenants": "SELECT * FROM tenants ORDER BY id DESC LIMIT ?",
        }
        sql = queries[table]
        if self._pg_url:
            import psycopg
            from psycopg.rows import dict_row

            pg_sql = sql.replace("?", "%s")
            with psycopg.connect(self._pg_url, row_factory=dict_row) as conn:
                cur = conn.execute(pg_sql, (limit,))
                return list(cur.fetchall())
        with self._sqlite() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def insert_tenant(
        self,
        tenant_type: str,
        tenant_id: str,
        display_name: str,
        settings: dict[str, Any],
    ) -> int:
        now = _utcnow()
        payload = json.dumps(settings)
        if self._pg_url:
            import psycopg

            with psycopg.connect(self._pg_url) as conn:
                cur = conn.execute(
                    """
                    INSERT INTO findings_tenants (tenant_type, tenant_id, display_name, settings, discovered_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s) RETURNING id
                    """,
                    (tenant_type, tenant_id, display_name, payload, now),
                )
                row = cur.fetchone()
                conn.commit()
                return int(row[0])
        with self._sqlite() as conn:
            cur = conn.execute(
                """
                INSERT INTO findings_tenants (tenant_type, tenant_id, display_name, settings, discovered_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tenant_type, tenant_id, display_name, payload, now),
            )
            conn.commit()
            return int(cur.lastrowid)

    def insert_oauth(self, row: dict[str, Any]) -> None:
        cols = (
            "tenant_type",
            "tenant_id",
            "app_name",
            "publisher",
            "scopes",
            "last_used",
            "risk_level",
            "observed_at",
        )
        vals = tuple(row.get(c) for c in cols)
        now = _utcnow()
        full = (*vals[:-1], vals[-1] or now)
        if self._pg_url:
            import psycopg

            with psycopg.connect(self._pg_url) as conn:
                conn.execute(
                    """
                    INSERT INTO findings_oauth (
                        tenant_type, tenant_id, app_name, publisher, scopes, last_used, risk_level, observed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    full,
                )
                conn.commit()
            return
        with self._sqlite() as conn:
            conn.execute(
                """
                INSERT INTO findings_oauth (
                    tenant_type, tenant_id, app_name, publisher, scopes, last_used, risk_level, observed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                full,
            )
            conn.commit()


def _sqlite_schema() -> str:
    return """
CREATE TABLE IF NOT EXISTS findings_tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    display_name TEXT,
    settings TEXT NOT NULL DEFAULT '{}',
    discovered_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS findings_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    setting_name TEXT NOT NULL,
    setting_value TEXT,
    observed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS findings_oauth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    publisher TEXT,
    scopes TEXT,
    last_used TEXT,
    risk_level TEXT NOT NULL DEFAULT 'unknown',
    observed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS findings_drift (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    setting_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    first_observed TEXT,
    last_observed TEXT,
    change_source TEXT DEFAULT 'unknown',
    observed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS findings_compliance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    framework TEXT NOT NULL,
    control_id TEXT NOT NULL,
    control_reference TEXT NOT NULL,
    finding_ref TEXT,
    mapped_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    tenant_type TEXT NOT NULL,
    client_id TEXT,
    schedule_cron TEXT,
    config TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""
