from typing import Any

from pydantic import BaseModel, Field


class Exposure(BaseModel):
    check_id: str
    severity: str
    public: bool = False
    title: str
    extra: dict[str, Any] = Field(default_factory=dict)
