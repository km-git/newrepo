"""Runtime configuration. Secrets come from the environment, never the repo."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from dmarc.paths import SEEDS_PATH, SELECTORS_PATH, output_dir

COMMON_DKIM_SELECTORS = (
    "google",
    "selector1",
    "selector2",
    "k1",
    "s1",
    "s2",
    "cm",
    "default",
)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def dkim_selectors(extra: list[str] | None = None) -> list[str]:
    configured = _load_yaml(SELECTORS_PATH)
    names: list[str] = []
    for value in configured.values():
        if isinstance(value, list):
            names.extend(str(item) for item in value)
        elif isinstance(value, str):
            names.append(value)
    names.extend(COMMON_DKIM_SELECTORS)
    if extra:
        names.extend(extra)
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        key = name.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def seed_accounts() -> list[dict]:
    data = _load_yaml(SEEDS_PATH)
    seeds = data.get("seeds") if isinstance(data, dict) else None
    return list(seeds or [])


@dataclass
class RuntimeConfig:
    domain: str = "example.com.au"
    output: Path = field(default_factory=output_dir)
    imap_host: str = ""
    imap_user: str = ""
    imap_pass: str = ""
    imap_folder: str = "INBOX"
    extra_selectors: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, **overrides: object) -> RuntimeConfig:
        cfg = cls(
            domain=str(overrides.get("domain") or os.environ.get("DMARC_DOMAIN") or "example.com.au"),
            output=Path(str(overrides.get("output") or output_dir())),
            imap_host=str(overrides.get("imap_host") or os.environ.get("DMARC_IMAP_HOST") or ""),
            imap_user=str(overrides.get("imap_user") or os.environ.get("DMARC_IMAP_USER") or ""),
            imap_pass=str(overrides.get("imap_pass") or os.environ.get("DMARC_IMAP_PASS") or ""),
            imap_folder=str(overrides.get("imap_folder") or os.environ.get("DMARC_IMAP_FOLDER") or "INBOX"),
            extra_selectors=list(overrides.get("extra_selectors") or []),
        )
        return cfg
