"""Discovery module — agentless data-store inventory."""

from __future__ import annotations

import json
from pathlib import Path

from dspm._cli_tools import run_cli
from dspm.models import StoreFinding
from dspm.sources.registry import discover as discover_uri

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def discover_any(uri: str, max_objects: int = 500) -> list[StoreFinding]:
    """Discover via unified sources connector (file, nfs, smb, s3, backup, m365, saas)."""
    objects = discover_uri(uri, max_objects=max_objects)
    return [
        StoreFinding(
            source=obj.uri,
            location=obj.path,
            provider=obj.provider,
            store_type=obj.store_type,
        )
        for obj in objects
    ]


def discover_directory(path: Path) -> list[StoreFinding]:
    findings: list[StoreFinding] = []
    if not path.exists():
        return findings
    if path.is_file():
        findings.append(
            StoreFinding(
                source=str(path.parent),
                location=path.name,
                provider="on-prem",
                store_type=path.suffix.lstrip(".") or "file",
            )
        )
        return findings
    for item in sorted(path.rglob("*")):
        if item.is_file() and item.suffix.lower() in {".csv", ".json", ".parquet", ".txt"}:
            findings.append(
                StoreFinding(
                    source=str(path),
                    location=str(item.relative_to(path)),
                    provider="on-prem",
                    store_type=item.suffix.lstrip("."),
                )
            )
    return findings


def discover_cloud(provider: str, profile: str | None = None) -> list[StoreFinding]:
    fixture = FIXTURES / f"cloudquery_{provider}.json"
    try:
        raw = run_cli(["cloudquery", "sync", "--help"], fixture_path=fixture)
    except Exception:
        raw = json.loads(fixture.read_text(encoding="utf-8")) if fixture.exists() else []
    if isinstance(raw, dict):
        items = raw.get("stores", [])
    else:
        items = raw if isinstance(raw, list) else []
    return [
        StoreFinding(
            source=item.get("source", provider),
            location=item.get("location", ""),
            provider=provider,
            store_type=item.get("store_type", "unknown"),
        )
        for item in items
    ]


def stores_to_dict(stores: list[StoreFinding]) -> list[dict]:
    return [s.model_dump() for s in stores]
