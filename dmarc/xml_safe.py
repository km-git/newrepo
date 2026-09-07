"""XML parse helper: always defusedxml (XXE-safe)."""

from __future__ import annotations

from defusedxml.ElementTree import ParseError, fromstring

__all__ = ["ParseError", "fromstring"]
