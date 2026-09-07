"""DuckDB persistence layer for DMARC findings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from dmarc.config import DATA_DIR, DB_PATH

_DUCKDB_DDL = """
CREATE TABLE IF NOT EXISTS findings_dns (
    domain VARCHAR, record_type VARCHAR, value VARCHAR,
    ttl INTEGER, last_checked_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS findings_spf (
    domain VARCHAR, record VARCHAR, dns_lookup_count INTEGER,
    lookups VARCHAR, all_qualifier VARCHAR, warnings VARCHAR, checked_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS findings_dkim (
    domain VARCHAR, selector VARCHAR, record VARCHAR,
    public_key_length INTEGER, warnings VARCHAR, checked_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS findings_dmarc (
    domain VARCHAR, source_org VARCHAR, source_ip VARCHAR, count INTEGER,
    disposition VARCHAR, dkim_result VARCHAR, spf_result VARCHAR,
    date_range VARCHAR, received_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS findings_forensic (
    domain VARCHAR, source_ip VARCHAR, from_address VARCHAR, subject VARCHAR,
    dkim_result VARCHAR, spf_result VARCHAR, received_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS findings_inbox (
    provider VARCHAR, seed_account VARCHAR, placement VARCHAR,
    subject VARCHAR, from_address VARCHAR, sent_at TIMESTAMP
);
"""


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect() -> duckdb.DuckDBPyConnection:
    ensure_dirs()
    conn = duckdb.connect(str(DB_PATH))
    conn.execute(_DUCKDB_DDL)
    return conn


def init_db() -> Path:
    conn = connect()
    conn.close()
    return DB_PATH


def clear_table(table: str) -> None:
    conn = connect()
    conn.execute(f"DELETE FROM {table}")
    conn.close()


def insert_rows(table: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn = connect()
    cols = list(rows[0].keys())
    placeholders = ", ".join(["?" for _ in cols])
    col_sql = ", ".join(cols)
    for row in rows:
        values = []
        for col in cols:
            val = row[col]
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            values.append(val)
        conn.execute(f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})", values)
    conn.close()
    return len(rows)


def fetch_all(table: str, limit: int = 500) -> list[dict[str, Any]]:
    conn = connect()
    result = conn.execute(f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT ?", [limit]).fetchall()
    cols = [d[0] for d in conn.description]
    conn.close()
    rows: list[dict[str, Any]] = []
    for row in result:
        item = dict(zip(cols, row, strict=False))
        for key in ("lookups", "warnings"):
            if key in item and isinstance(item[key], str):
                try:
                    item[key] = json.loads(item[key])
                except json.JSONDecodeError:
                    pass
        rows.append(item)
    return rows


def count_rows(table: str) -> int:
    conn = connect()
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return int(n)
