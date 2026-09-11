from typing import Any

from pydantic import BaseModel, Field


class EncryptionFinding(BaseModel):
    target: str
    at_rest: bool = False
    in_flight: bool = False
    scanner: str
    extra: dict[str, Any] = Field(default_factory=dict)
