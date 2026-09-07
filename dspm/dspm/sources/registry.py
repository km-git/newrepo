"""Connector registry — dispatches URIs to source handlers."""

from __future__ import annotations

from dspm.sources.connectors.archive import ArchiveConnector
from dspm.sources.connectors.local import LocalConnector
from dspm.sources.connectors.m365 import M365Connector
from dspm.sources.connectors.s3 import S3Connector
from dspm.sources.connectors.saas import SaasConnector
from dspm.sources.connectors.smb import SmbConnector
from dspm.sources.models import DataObject, ObjectPreview, SourceScanResult
from dspm.sources.uri import parse_uri

_CONNECTORS = {
    "file": LocalConnector(),
    "nfs": LocalConnector(),  # NFS = mounted path
    "backup": ArchiveConnector(),
    "archive": ArchiveConnector(),
    "s3": S3Connector(),
    "smb": SmbConnector(),
    "m365": M365Connector(),
    "saas": SaasConnector(),
}

SUPPORTED_SCHEMES = list(_CONNECTORS.keys())


def get_connector(uri: str):
    scheme, _ = parse_uri(uri)
    if scheme not in _CONNECTORS:
        raise ValueError(f"unsupported scheme '{scheme}'. Supported: {SUPPORTED_SCHEMES}")
    return _CONNECTORS[scheme]


def discover(uri: str, max_objects: int = 500) -> list[DataObject]:
    return get_connector(uri).discover(uri, max_objects=max_objects)


def preview(uri: str, path: str = "", max_bytes: int = 8192) -> ObjectPreview:
    return get_connector(uri).preview(uri, path=path, max_bytes=max_bytes)


def scan_and_classify(uri: str, max_objects: int = 200, classify_limit: int = 50) -> SourceScanResult:
    from dspm.sources.scanner import scan_source

    return scan_source(uri, max_objects=max_objects, classify_limit=classify_limit)
