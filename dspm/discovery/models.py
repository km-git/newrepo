from typing import Any

from pydantic import BaseModel, Field


class Store(BaseModel):
    provider: str
    kind: str
    location: str
    name: str = ""
    managed: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)
