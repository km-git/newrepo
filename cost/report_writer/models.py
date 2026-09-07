"""Pydantic models for report_writer."""

from pydantic import BaseModel, Field


class ReportWriterResult(BaseModel):
    module: str = Field(default="report_writer")
    ok: bool = True
    count: int = 0
