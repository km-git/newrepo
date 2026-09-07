from typing import Any

from pydantic import BaseModel


class Risk(BaseModel):
    finding_id: str
    score: int
    vector: dict[str, Any]
    suggested_action: str
    title: str = ""
