"""SQLite findings store (Postgres 17 via docker-compose is optional)."""

from dspm.db.store import FindingsStore, connect, default_db_path

__all__ = ["FindingsStore", "connect", "default_db_path"]
