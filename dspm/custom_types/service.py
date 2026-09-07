"""YAML registry of Presidio-style custom recognizers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from dspm.classification.checksums import abn_checksum_ok, nhs_checksum_ok, tfn_plausible
from dspm.classification.recognizers import Pattern, PatternRecognizer

REGISTRY_PATH = Path(__file__).with_name("registry.yaml")


class CustomType(BaseModel):
    name: str
    pattern: str
    context_words: list[str] = Field(default_factory=list)
    score_threshold: float = Field(ge=0, le=1)
    finding_type: str = "custom"
    description: str = ""


class Registry(BaseModel):
    types: list[CustomType]


def load_registry(path: Path | None = None) -> Registry:
    raw = yaml.safe_load((path or REGISTRY_PATH).read_text(encoding="utf-8")) or {}
    items = raw.get("types") if isinstance(raw, dict) else raw
    rows = list(items or [])
    return Registry(types=[CustomType.model_validate(item) for item in rows])


def recognizers_from_registry(path: Path | None = None) -> list[PatternRecognizer]:
    return [
        PatternRecognizer(
            name=item.name,
            patterns=[Pattern(item.name, item.pattern, max(item.score_threshold, 0.7))],
            context_words=item.context_words,
            score_threshold=item.score_threshold,
            finding_type=item.finding_type,
        )
        for item in load_registry(path).types
    ]


def test_type(name: str, sample: str, path: Path | None = None) -> dict[str, Any]:
    recs = {r.name: r for r in recognizers_from_registry(path)}
    if name not in recs:
        raise KeyError(f"unknown custom type {name!r}")
    matches = recs[name].analyze(sample, column=name)
    extra = {}
    if name == "au_tfn":
        extra["checksum"] = tfn_plausible(sample)
    if name == "au_abn":
        extra["checksum"] = abn_checksum_ok(sample)
    if name == "nhs_number":
        extra["checksum"] = nhs_checksum_ok(sample)
    return {
        "type": name,
        "sample_preview": sample[:4] + "…",
        "matched": bool(matches),
        "confidence": matches[0].score if matches else 0.0,
        **extra,
    }
