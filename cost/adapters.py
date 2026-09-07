"""Cloud inventory adapters. Live APIs when credentials exist; sandbox otherwise."""

from __future__ import annotations

import json
from typing import Any

from cost.fixtures import resources_for
from cost.settings import sandbox_mode
from cost.subprocess_tools import CliUnavailable, steampipe_query

AWS_STEAMPIPE_SQL = """
select instance_id as resource_id, 'ec2' as resource_type, region, instance_type,
       tags, 'running' as name
from aws_ec2_instance
limit 500
"""


def list_resources(provider: str, **_kwargs: Any) -> tuple[list[dict[str, Any]], str]:
    """Return (resources, source). source is sandbox | steampipe | sdk."""
    if sandbox_mode():
        return resources_for(provider), "sandbox"
    try:
        rows = steampipe_query(_steampipe_sql(provider))
        if rows:
            return [_normalize_steampipe(provider, r) for r in rows], "steampipe"
    except (CliUnavailable, RuntimeError, json.JSONDecodeError, OSError):
        pass
    sdk_rows = _sdk_inventory(provider, **_kwargs)
    if sdk_rows:
        return sdk_rows, "sdk"
    return resources_for(provider), "sandbox-fallback"


def _steampipe_sql(provider: str) -> str:
    if provider == "azure":
        return "select id as resource_id, type as resource_type, location as region from azure_compute_virtual_machine limit 500"
    if provider == "gcp":
        return "select self_link as resource_id, 'gce' as resource_type, location as region from gcp_compute_instance limit 500"
    return AWS_STEAMPIPE_SQL


def _normalize_steampipe(provider: str, row: dict[str, Any]) -> dict[str, Any]:
    tags = row.get("tags") or {}
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except json.JSONDecodeError:
            tags = {}
    return {
        "provider": provider,
        "account_id": str(row.get("account_id") or row.get("subscription_id") or row.get("project") or "unknown"),
        "region": str(row.get("region") or row.get("location") or ""),
        "resource_id": str(row.get("resource_id") or row.get("id") or row.get("instance_id") or ""),
        "resource_type": str(row.get("resource_type") or row.get("type") or "unknown"),
        "name": str(row.get("name") or row.get("title") or ""),
        "tags": tags if isinstance(tags, dict) else {},
        "monthly_cost": float(row.get("monthly_cost") or 0),
        "config": {k: v for k, v in row.items() if k not in {"tags", "resource_id", "resource_type"}},
    }


def _sdk_inventory(provider: str, **kwargs: Any) -> list[dict[str, Any]]:
    if provider == "aws":
        return _boto3_ec2(kwargs.get("profile") or "", kwargs.get("regions") or "ap-southeast-2")
    if provider == "azure":
        return _azure_rm(kwargs)
    if provider == "gcp":
        return _gcp_rm(kwargs)
    return []


def _boto3_ec2(profile: str, regions: str) -> list[dict[str, Any]]:
    try:
        import boto3
    except ImportError:
        return []
    session = boto3.Session(profile_name=profile or None)
    out: list[dict[str, Any]] = []
    for region in [r.strip() for r in regions.split(",") if r.strip()]:
        try:
            client = session.client("ec2", region_name=region)
            resp = client.describe_instances()
        except Exception:
            continue
        for reservation in resp.get("Reservations") or []:
            for inst in reservation.get("Instances") or []:
                tags = {t.get("Key"): t.get("Value") for t in inst.get("Tags") or [] if t.get("Key")}
                out.append(
                    {
                        "provider": "aws",
                        "account_id": str(inst.get("OwnerId") or ""),
                        "region": region,
                        "resource_id": inst.get("InstanceId"),
                        "resource_type": "ec2",
                        "name": tags.get("Name", ""),
                        "tags": tags,
                        "monthly_cost": 0.0,
                        "config": {
                            "instance_type": inst.get("InstanceType"),
                            "state": (inst.get("State") or {}).get("Name"),
                        },
                    }
                )
    return out


def _azure_rm(kwargs: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.resource import ResourceManagementClient
    except ImportError:
        return []
    sub = kwargs.get("subscription_id") or ""
    if not sub:
        return []
    try:
        client = ResourceManagementClient(DefaultAzureCredential(), sub)
        out = []
        for item in client.resources.list():
            tags = dict(item.tags or {})
            out.append(
                {
                    "provider": "azure",
                    "account_id": sub,
                    "region": item.location or "",
                    "resource_id": item.id,
                    "resource_type": item.type or "resource",
                    "name": item.name or "",
                    "tags": tags,
                    "monthly_cost": 0.0,
                    "config": {"type": item.type},
                }
            )
        return out
    except Exception:
        return []


def _gcp_rm(kwargs: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from google.cloud import resourcemanager_v3
    except ImportError:
        return []
    project = kwargs.get("project_id") or ""
    if not project:
        return []
    try:
        client = resourcemanager_v3.ProjectsClient()
        proj = client.get_project(name=f"projects/{project}")
        labels = dict(proj.labels or {})
        return [
            {
                "provider": "gcp",
                "account_id": project,
                "region": "global",
                "resource_id": proj.name,
                "resource_type": "project",
                "name": proj.display_name or project,
                "tags": labels,
                "monthly_cost": 0.0,
                "config": {"state": str(proj.state)},
            }
        ]
    except Exception:
        return []
