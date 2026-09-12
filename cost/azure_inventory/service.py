"""cost/azure_inventory — read-only Azure resource inventory."""

from __future__ import annotations

from typing import Any

from cost.adapters import list_resources
from cost.persist import persist_resources


def run(
    *,
    sandbox: bool = True,
    subscription_id: str = "",
    tenant_id: str = "",
    client_id: str = "",
    **_kwargs: Any,
) -> dict[str, Any]:
    resources, source = list_resources(
        "azure",
        subscription_id=subscription_id,
        tenant_id=tenant_id,
        client_id=client_id,
    )
    count = persist_resources(resources, source)
    return {
        "provider": "azure",
        "source": source,
        "resource_count": count,
        "resources": resources,
        "sandbox": sandbox,
    }
