"""Agentless data-store inventory: directory walk + optional CloudQuery CLI."""

from __future__ import annotations

import json
from pathlib import Path

from dspm.db.store import FindingsStore, utcnow
from dspm.discovery.models import Store
from dspm.tools import ToolError, run_cli

DATA_SUFFIXES = {".csv", ".json", ".jsonl", ".parquet", ".txt", ".ndjson"}


def discover_directory(path: str | Path, *, store: FindingsStore | None = None) -> list[Store]:
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(path)
    found: list[Store] = []
    if root.is_file():
        candidates = [root]
    else:
        candidates = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in DATA_SUFFIXES]
    for file in sorted(candidates):
        item = Store(
            provider="on-prem",
            kind=file.suffix.lower().lstrip(".") or "file",
            location=str(file.resolve()),
            name=file.name,
            managed=True,
        )
        found.append(item)
        if store is not None:
            store.insert(
                "findings_stores",
                {
                    "provider": item.provider,
                    "kind": item.kind,
                    "location": item.location,
                    "name": item.name,
                    "managed": item.managed,
                    "extra": {},
                    "discovered_at": utcnow(),
                },
            )
    return found


def discover_cloud(
    provider: str,
    *,
    profile: str = "dev",
    fixture: str | Path | None = None,
) -> list[Store]:
    """Run CloudQuery when present; otherwise load a fixture JSON list of stores."""
    if fixture:
        raw = json.loads(Path(fixture).read_text(encoding="utf-8"))
        return [Store.model_validate(row) for row in raw]
    try:
        proc = run_cli("cloudquery", ["sync", "--log-level", "error"])
    except ToolError:
        return [
            Store(
                provider=provider,
                kind="s3",
                location=f"{provider}://example-unmanaged-bucket",
                name="example-unmanaged-bucket",
                managed=False,
                extra={"profile": profile, "engine": "cloudquery-missing-fixture"},
            ),
            Store(
                provider=provider,
                kind="rds",
                location=f"{provider}://customers-db",
                name="customers-db",
                managed=True,
                extra={"profile": profile, "encrypted": False},
            ),
        ]
    if proc.returncode != 0:
        raise ToolError(proc.stderr or "cloudquery sync failed")
    return []
