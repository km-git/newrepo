"""Base connector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dspm.sources.models import DataObject, ObjectPreview


class BaseConnector(ABC):
    provider: str = "unknown"

    @abstractmethod
    def discover(self, uri: str, max_objects: int = 500) -> list[DataObject]:
        raise NotImplementedError

    @abstractmethod
    def preview(self, uri: str, path: str = "", max_bytes: int = 8192) -> ObjectPreview:
        raise NotImplementedError

    def supports_classification(self) -> bool:
        return True
