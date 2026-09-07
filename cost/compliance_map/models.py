"""Pydantic models for compliance_map."""

from pydantic import BaseModel, Field


class ComplianceMapResult(BaseModel):
    module: str = Field(default="compliance_map")
    ok: bool = True
    count: int = 0
