from typing import Any

from pydantic import BaseModel, Field


class ShadowAsset(BaseModel):
    location: str
    kind: str
    reason: str
    extra: dict[str, Any] = Field(default_factory=dict)
