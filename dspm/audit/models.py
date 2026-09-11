from typing import Any

from pydantic import BaseModel, Field


class ToolRecord(BaseModel):
    name: str
    package: str
    version: str
    license: str
    role: str
    module: str
    on_path: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)
