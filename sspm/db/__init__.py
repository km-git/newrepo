"""Findings store (SQLite default; Postgres via SSPM_DATABASE_URL)."""

from __future__ import annotations

from sspm.db.store import FindingsStore, connect, default_db_path, utcnow

__all__ = ["FindingsStore", "connect", "default_db_path", "utcnow"]
