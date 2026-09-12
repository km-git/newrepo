"""Shared platform runtime context."""

from __future__ import annotations

from pathlib import Path

from .constants import DEFAULT_DATA_DIR
from .jobs import JobStore
from .storage import VaultStorage


class PlatformContext:
    """Shared runtime context for module handlers."""

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.jobs = JobStore(self.data_dir)
        self.vault = VaultStorage(self.data_dir)
        self.manifests_dir = self.data_dir / "manifests"
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
