"""cost/gcp_inventory — read-only GCP resource inventory."""

from __future__ import annotations

from typing import Any

from cost.adapters import list_resources
from cost.persist import persist_resources


def run(*, sandbox: bool = True, project_id: str = "", service_account: str = "", **_kwargs: Any) -> dict[str, Any]:
    resources, source = list_resources("gcp", project_id=project_id, service_account=service_account)
    count = persist_resources(resources, source)
    return {
        "provider": "gcp",
        "source": source,
        "resource_count": count,
        "resources": resources,
        "sandbox": sandbox,
    }
