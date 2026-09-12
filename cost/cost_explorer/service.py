"""cost/cost_explorer — daily/monthly rollup. Cost APIs lag 24-48h."""

from __future__ import annotations

from typing import Any

from cost.db.store import dumps
from cost.fixtures import costs_for, tenant_id
from cost.persist import persist_named
from cost.settings import sandbox_mode

LAG_NOTE = "Cost data has a 24-48 hour lag; this review does not promise real-time figures."


def run(*, sandbox: bool = True, provider: str = "aws", since: str = "30d", **_kwargs: Any) -> dict[str, Any]:
    rows = costs_for(None if provider == "all" else provider)
    if not sandbox_mode() and not sandbox:
        live = _live_costs(provider, since)
        if live:
            rows = live
    stored = []
    for row in rows:
        stored.append(
            {
                "tenant_id": tenant_id(),
                "provider": row["provider"],
                "account_id": row.get("account_id") or "",
                "region": row.get("region") or "",
                "service": row["service"],
                "period": row.get("period") or since,
                "amount": float(row.get("amount") or 0),
                "tag_key": row.get("tag_key") or "",
                "tag_value": row.get("tag_value") or "",
            }
        )
    persist_named("findings_costs", stored)
    total = round(sum(r["amount"] for r in stored), 2)
    by_service: dict[str, float] = {}
    for row in stored:
        by_service[row["service"]] = round(by_service.get(row["service"], 0) + row["amount"], 2)
    return {
        "provider": provider,
        "since": since,
        "lag_note": LAG_NOTE,
        "total": total,
        "by_service": by_service,
        "rows": stored,
        "sandbox": sandbox or sandbox_mode(),
        "sql_engine": _sql_engine(),
        "meta": dumps({"since": since}),
    }


def _sql_engine() -> str:
    try:
        import duckdb  # noqa: F401

        return "duckdb"
    except ImportError:
        return "sqlite"


def _live_costs(provider: str, since: str) -> list[dict[str, Any]]:
    if provider == "aws":
        return _aws_ce(since)
    return []


def _aws_ce(since: str) -> list[dict[str, Any]]:
    try:
        from datetime import UTC, datetime, timedelta

        import boto3

        days = int(since.rstrip("d")) if since.endswith("d") else 30
        end = datetime.now(UTC).date()
        start = end - timedelta(days=days)
        client = boto3.client("ce")
        resp = client.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        out = []
        for result in resp.get("ResultsByTime") or []:
            period = (result.get("TimePeriod") or {}).get("Start", "")[:7]
            for group in result.get("Groups") or []:
                keys = group.get("Keys") or ["unknown"]
                amount = float((group.get("Metrics") or {}).get("UnblendedCost", {}).get("Amount") or 0)
                out.append(
                    {
                        "provider": "aws",
                        "account_id": "",
                        "region": "",
                        "service": keys[0],
                        "period": period,
                        "amount": amount,
                        "tag_key": "",
                        "tag_value": "",
                    }
                )
        return out
    except Exception:
        return []
