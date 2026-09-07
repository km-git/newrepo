"""Disclaimer models."""

from __future__ import annotations

from pydantic import BaseModel


class Disclaimer(BaseModel):
    name: str
    text: str
    path: str
