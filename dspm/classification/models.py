from __future__ import annotations

from pydantic import BaseModel, Field


class Finding(BaseModel):
    source: str
    location: str
    type: str
    confidence: float = Field(ge=0, le=1)
    verdict: str
    suggested_action: str = ""
    recognizer: str = ""
    value_preview: str = ""


class ClassifyResult(BaseModel):
    findings: list[Finding]
    engine: str
    source: str
    rows_scanned: int = 0
