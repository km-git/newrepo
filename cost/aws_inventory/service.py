"""cost/aws_inventory — read-only AWS resource inventory."""

from __future__ import annotations

from typing import Any

from cost.adapters import list_resources
from cost.persist import persist_resources


def run(*, sandbox: bool = True, profile: str = "", regions: str = "ap-southeast-2", **_kwargs: Any) -> dict[str, Any]:
    resources, source = list_resources("aws", profile=profile, regions=regions)
    count = persist_resources(resources, source)
    return {
        "provider": "aws",
        "source": source,
        "resource_count": count,
        "resources": resources,
        "profile": profile,
        "regions": regions,
        "sandbox": sandbox,
    }
