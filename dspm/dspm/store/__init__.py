"""Persistence layer — SQLite default, Postgres optional."""

from dspm.store.db import get_connection, init_db, persist_scan_results

__all__ = ["get_connection", "init_db", "persist_scan_results"]
