"""Pydantic models for audit."""

from pydantic import BaseModel, Field


class AuditResult(BaseModel):
    module: str = Field(default="audit")
    ok: bool = True
    count: int = 0
