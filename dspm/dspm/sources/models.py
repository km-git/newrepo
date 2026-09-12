"""Unified data source models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DataObject(BaseModel):
    """A discoverable object from any connector."""

    uri: str
    path: str
    name: str
    provider: str
    store_type: str
    size_bytes: int | None = None
    mime_type: str | None = None
    modified_at: str | None = None
    parent_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObjectPreview(BaseModel):
    uri: str
    path: str
    content_type: str
    preview_text: str
    truncated: bool = False
    size_bytes: int | None = None


class SourceScanResult(BaseModel):
    source_uri: str
    provider: str
    objects: list[DataObject]
    object_count: int
    findings: list[dict] = Field(default_factory=list)
