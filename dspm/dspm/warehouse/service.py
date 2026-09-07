"""SQL warehouse — Databricks/Snowflake inspired DuckDB workspace."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import duckdb

from dspm.store.db import fetch_all, init_db, insert_row

BLOCKED_KEYWORDS = {"drop", "delete", "truncate", "insert", "update", "attach", "copy"}


def execute_sql(sql: str, user: str = "analyst", read_only: bool = True) -> dict[str, Any]:
    init_db()
    normalized = sql.strip().lower()
    if read_only:
        first_word = normalized.split()[0] if normalized else ""
        if first_word in BLOCKED_KEYWORDS:
            raise ValueError(f"blocked keyword in read-only mode: {first_word}")
    start = time.perf_counter()
    conn = duckdb.connect(":memory:")
    try:
        conn.execute(
            """
            CREATE TABLE findings AS SELECT * FROM (
                VALUES
                ('s3://bucket', 'email', 'PII', 0.95, 'sensitive'),
                ('rds://db', 'ssn', 'PII', 0.92, 'sensitive'),
                ('s3://public', 'card', 'PCI', 0.88, 'public')
            ) AS t(source, location, type, confidence, verdict)
            """
        )
        result = conn.execute(sql)
        columns = [d[0] for d in result.description]
        raw_rows = result.fetchall()
        duration_ms = (time.perf_counter() - start) * 1000
        rows = [dict(zip(columns, row)) for row in raw_rows]
        insert_row(
            "query_history",
            {
                "sql_text": sql,
                "engine": "duckdb",
                "duration_ms": duration_ms,
                "row_count": len(rows),
                "user_name": user,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return {"columns": columns, "rows": rows, "duration_ms": round(duration_ms, 2)}
    finally:
        conn.close()


def query_history(limit: int = 20) -> list[dict]:
    return fetch_all("query_history", limit=limit)
