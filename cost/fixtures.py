"""Load sandbox fixtures and shared resource helpers."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from cost.paths import FIXTURES_PATH


@lru_cache(maxsize=1)
def load_sandbox() -> dict[str, Any]:
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def resources_for(provider: str | None = None) -> list[dict[str, Any]]:
    rows = list(load_sandbox().get("resources") or [])
    if provider and provider != "all":
        return [r for r in rows if r.get("provider") == provider]
    return rows


def costs_for(provider: str | None = None) -> list[dict[str, Any]]:
    rows = list(load_sandbox().get("costs") or [])
    if provider and provider != "all":
        return [r for r in rows if r.get("provider") == provider]
    return rows


def baseline_rows() -> list[dict[str, Any]]:
    return list(load_sandbox().get("baseline") or [])


def tenant_id() -> str:
    return str(load_sandbox().get("tenant_id") or "sandbox-demo")


def tenant_name() -> str:
    return str(load_sandbox().get("tenant_name") or "sandbox")
