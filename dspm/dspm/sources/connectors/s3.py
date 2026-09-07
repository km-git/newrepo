"""S3 and S3-compatible object storage connector."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dspm.sources.connectors.base import BaseConnector
from dspm.sources.models import DataObject, ObjectPreview

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "s3_objects.json"


class S3Connector(BaseConnector):
    provider = "s3"

    def _parse_s3_uri(self, uri: str) -> tuple[str, str]:
        parsed = urlparse(uri)
        bucket = parsed.netloc
        prefix = parsed.path.lstrip("/")
        return bucket, prefix

    def discover(self, uri: str, max_objects: int = 500) -> list[DataObject]:
        bucket, prefix = self._parse_s3_uri(uri)
        objects: list[DataObject] = []
        try:
            import boto3
            from botocore import UNSIGNED
            from botocore.config import Config

            endpoint = os.environ.get("DSPM_S3_ENDPOINT")
            kwargs = {}
            if endpoint:
                kwargs["endpoint_url"] = endpoint
            if not os.environ.get("AWS_ACCESS_KEY_ID"):
                kwargs["config"] = Config(signature_version=UNSIGNED)
            client = boto3.client("s3", **kwargs)
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    if len(objects) >= max_objects:
                        break
                    key = item["Key"]
                    objects.append(
                        DataObject(
                            uri=uri,
                            path=key,
                            name=key.split("/")[-1],
                            provider="s3",
                            store_type="object",
                            size_bytes=item.get("Size"),
                            modified_at=item.get("LastModified", datetime.now(timezone.utc)).isoformat()
                            if hasattr(item.get("LastModified"), "isoformat")
                            else str(item.get("LastModified", "")),
                            parent_uri=uri,
                            metadata={"bucket": bucket, "etag": item.get("ETag", "")},
                        )
                    )
            if objects:
                return objects
        except Exception:
            pass
        return self._fixture_objects(uri, bucket, prefix, max_objects)

    def _fixture_objects(self, uri: str, bucket: str, prefix: str, limit: int) -> list[DataObject]:
        if not FIXTURES.exists():
            return []
        data = json.loads(FIXTURES.read_text(encoding="utf-8"))
        items = data.get("objects", [])
        objects = []
        for item in items[:limit]:
            if prefix and not item.get("key", "").startswith(prefix):
                continue
            objects.append(
                DataObject(
                    uri=uri,
                    path=item["key"],
                    name=item["key"].split("/")[-1],
                    provider="s3",
                    store_type="object",
                    size_bytes=item.get("size"),
                    parent_uri=uri,
                    metadata={"bucket": bucket},
                )
            )
        return objects

    def preview(self, uri: str, path: str = "", max_bytes: int = 8192) -> ObjectPreview:
        bucket, _ = self._parse_s3_uri(uri)
        key = path
        try:
            import boto3

            client = boto3.client("s3", endpoint_url=os.environ.get("DSPM_S3_ENDPOINT"))
            resp = client.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{max_bytes - 1}")
            raw = resp["Body"].read()
            text = raw.decode("utf-8", errors="replace")
            return ObjectPreview(
                uri=uri, path=key, content_type="text", preview_text=text, truncated=True, size_bytes=resp.get("ContentLength")
            )
        except Exception:
            pass
        if FIXTURES.exists():
            data = json.loads(FIXTURES.read_text(encoding="utf-8"))
            for item in data.get("objects", []):
                if item.get("key") == key and "preview" in item:
                    return ObjectPreview(
                        uri=uri, path=key, content_type="text", preview_text=item["preview"], truncated=False
                    )
        return ObjectPreview(uri=uri, path=key, content_type="unknown", preview_text="")
