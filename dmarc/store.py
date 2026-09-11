"""SQLite findings store (DuckDB view when the optional extra is present)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dmarc.paths import db_path, output_dir

TABLES = (
    "findings_dns",
    "findings_spf",
    "findings_dkim",
    "findings_dmarc",
    "findings_forensic",
    "findings_inbox",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings_dns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  record_type TEXT NOT NULL,
  value TEXT,
  ttl INTEGER,
  last_checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_spf (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  record TEXT,
  dns_lookup_count INTEGER,
  lookups TEXT,
  all_qualifier TEXT,
  warnings TEXT,
  last_checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_dkim (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  selector TEXT,
  record TEXT,
  public_key_length INTEGER,
  warnings TEXT,
  last_checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_dmarc (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  source_org TEXT,
  source_ip TEXT,
  count INTEGER,
  disposition TEXT,
  dkim_result TEXT,
  spf_result TEXT,
  date_range TEXT,
  received_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_forensic (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  source_ip TEXT,
  from_address TEXT,
  subject TEXT,
  dkim_result TEXT,
  spf_result TEXT,
  received_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings_inbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT,
  seed_account TEXT,
  placement TEXT,
  subject TEXT,
  from_address TEXT,
  sent_at TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def connect(root: Path | None = None) -> sqlite3.Connection:
    path = db_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def insert_rows(table: str, rows: Iterable[dict[str, Any]], root: Path | None = None) -> int:
    if table not in TABLES:
        raise ValueError(f"unknown table {table}")
    rows = list(rows)
    if not rows:
        return 0
    conn = connect(root)
    try:
        keys = list(rows[0].keys())
        placeholders = ",".join("?" for _ in keys)
        cols = ",".join(keys)
        conn.executemany(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",  # noqa: S608 — table/cols from TABLES whitelist
            [tuple(row[k] for k in keys) for row in rows],
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def fetch_all(table: str, domain: str | None = None, root: Path | None = None, since: str | None = None) -> list[dict]:
    if table not in TABLES:
        raise ValueError(f"unknown table {table}")
    conn = connect(root)
    try:
        sql = f"SELECT * FROM {table}"  # noqa: S608 — table name from TABLES whitelist
        params: list[Any] = []
        clauses: list[str] = []
        if domain and "domain" in _columns(conn, table):
            clauses.append("domain = ?")
            params.append(domain)
        if since:
            stamp_col = "received_at" if "received_at" in _columns(conn, table) else "last_checked_at"
            if stamp_col in _columns(conn, table):
                clauses.append(f"{stamp_col} >= ?")
                params.append(since)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        cur = conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def dump_json(name: str, payload: Any, root: Path | None = None) -> Path:
    dest = output_dir(root) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return dest


def duckdb_view_sql() -> str:
    """SQL the operator can run in DuckDB over the SQLite file (optional extra)."""
    return (
        "INSTALL sqlite; LOAD sqlite;\n"
        "CREATE OR REPLACE VIEW dmarc_pass_fail AS\n"
        "SELECT domain, source_org, disposition, dkim_result, spf_result, count\n"
        "FROM sqlite_scan('dmarc.sqlite3', 'findings_dmarc');\n"
    )
