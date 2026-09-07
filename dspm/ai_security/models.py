from typing import Any

from pydantic import BaseModel, Field


class AiFinding(BaseModel):
    store: str
    location: str
    type: str
    confidence: float
    warning: str
    extra: dict[str, Any] = Field(default_factory=dict)
