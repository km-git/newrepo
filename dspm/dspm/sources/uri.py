"""URI parsing for source connectors."""

from __future__ import annotations

from urllib.parse import urlparse


def parse_uri(uri: str) -> tuple[str, str]:
    if "://" not in uri:
        uri = f"file://{uri}"
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()
    location = f"{parsed.netloc}{parsed.path}" if parsed.netloc else parsed.path
    return scheme, location
