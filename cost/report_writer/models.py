"""Pydantic models for cost/report_writer."""

from __future__ import annotations

from pydantic import BaseModel


class ModuleMeta(BaseModel):
    module: str = "report_writer"
    kind: str = "cost-observation"


class ReportMeta(BaseModel):
    title: str = "Cloud Cost & Configuration Review"
    provider: str = "all"
