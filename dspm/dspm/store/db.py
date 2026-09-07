"""SQLite/Postgres persistence for findings, events, and query history."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

DEFAULT_DB = Path(os.environ.get("DSPM_DB_PATH", "output/dspm/dspm.db"))


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    path = db_path or DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> Path:
    path = db_path or DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT, location TEXT, type TEXT, confidence REAL,
                verdict TEXT, suggested_action TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS risk_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finding_id INTEGER, score REAL, vector TEXT,
                suggested_action TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS exposures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource TEXT, exposure_type TEXT, severity TEXT,
                details TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS catalog_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urn TEXT UNIQUE, name TEXT, asset_type TEXT,
                owner TEXT, tags TEXT, lineage_parent TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS governance_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, policy_type TEXT, framework TEXT,
                definition TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS siem_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT, severity TEXT, source TEXT,
                message TEXT, raw TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS observability_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT, value REAL, labels TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, condition TEXT, threshold REAL,
                enabled INTEGER DEFAULT 1, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sql_text TEXT, engine TEXT, duration_ms REAL,
                row_count INTEGER, user_name TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS source_objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_uri TEXT, path TEXT, name TEXT, provider TEXT,
                store_type TEXT, size_bytes INTEGER, metadata TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS source_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_uri TEXT, provider TEXT, object_count INTEGER,
                finding_count INTEGER, created_at TEXT
            );
            """
        )
    return path


def persist_scan_results(
    findings: list[dict],
    risks: list[dict] | None = None,
    exposures: list[dict] | None = None,
    db_path: Path | None = None,
) -> dict[str, int]:
    init_db(db_path)
    counts = {"findings": 0, "risks": 0, "exposures": 0}
    now = _utcnow()
    with get_connection(db_path) as conn:
        for f in findings:
            conn.execute(
                """INSERT INTO findings (source, location, type, confidence, verdict, suggested_action, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    f.get("source"),
                    f.get("location"),
                    f.get("type"),
                    f.get("confidence"),
                    f.get("verdict"),
                    f.get("suggested_action"),
                    now,
                ),
            )
            counts["findings"] += 1
        for r in risks or []:
            conn.execute(
                """INSERT INTO risk_scores (finding_id, score, vector, suggested_action, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (r.get("finding_id"), r.get("score"), r.get("vector"), r.get("suggested_action"), now),
            )
            counts["risks"] += 1
        for e in exposures or []:
            conn.execute(
                """INSERT INTO exposures (resource, exposure_type, severity, details, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    e.get("resource"),
                    e.get("exposure_type"),
                    e.get("severity"),
                    json.dumps(e.get("details", {})),
                    now,
                ),
            )
            counts["exposures"] += 1
    return counts


def fetch_all(table: str, limit: int = 100, db_path: Path | None = None) -> list[dict[str, Any]]:
    allowed = {
        "findings",
        "risk_scores",
        "exposures",
        "catalog_assets",
        "governance_policies",
        "siem_events",
        "observability_metrics",
        "alert_rules",
        "query_history",
        "source_objects",
        "source_scans",
    }
    if table not in allowed:
        raise ValueError(f"unknown table: {table}")
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def insert_row(table: str, data: dict[str, Any], db_path: Path | None = None) -> int:
    allowed = {
        "findings", "risk_scores", "exposures", "catalog_assets",
        "governance_policies", "siem_events", "observability_metrics",
        "alert_rules", "query_history", "source_objects", "source_scans",
    }
    if table not in allowed:
        raise ValueError(f"unknown table: {table}")
    init_db(db_path)
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    with get_connection(db_path) as conn:
        cur = conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            tuple(data.values()),
        )
        return int(cur.lastrowid or 0)
