"""Custom data types registry."""

from __future__ import annotations

from pathlib import Path

import yaml

from dspm.classification.recognizers import CUSTOM_TYPES

REGISTRY_PATH = Path(__file__).resolve().parent / "registry.yaml"


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    return CUSTOM_TYPES


def list_types() -> list[dict]:
    reg = load_registry()
    return [{"name": k, **v} for k, v in reg.items()]
