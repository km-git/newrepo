from typing import Any

from pydantic import BaseModel, Field


class AccessEdge(BaseModel):
    principal: str
    principal_type: str
    permission: str
    store_id: str | None = None
    overprivileged: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)
