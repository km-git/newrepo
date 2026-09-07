"""XML parse helper: prefer defusedxml when installed."""

from __future__ import annotations

from xml.etree.ElementTree import Element


def fromstring(xml_text: str) -> Element:
    try:
        from defusedxml.ElementTree import fromstring as _fromstring
    except ImportError:
        from xml.etree.ElementTree import fromstring as _fromstring
    return _fromstring(xml_text)  # noqa: S314 — operator-owned RUA/RUF; defusedxml when installed
