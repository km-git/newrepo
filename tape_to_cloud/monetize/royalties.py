"""Royalty reporting on top of an append-only usage ledger.

Access/usage events (asset, consumer, bytes, requests, timestamp) are recorded
as JSONL lines; royalty reports aggregate them per licensor over a period
against rate cards (per-GB, per-request, or flat license fee). All money math
uses ``Decimal`` for determinism.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable

from ._audit import append_audit, utc_now_iso
from .licensing import LicenseStore, _parse_utc

LEDGER_FILENAME = "usage_ledger.jsonl"
RATE_MODELS = ("per_gb", "per_request", "flat")
BYTES_PER_GB = Decimal(10) ** 9
_CENT = Decimal("0.01")


class RoyaltyError(ValueError):
    """Raised for invalid rate cards, events, or report parameters."""


@dataclass(frozen=True)
class RateCard:
    """Pricing for one license id: per-GB, per-request, or flat fee."""

    license_id: str
    model: str
    rate: Decimal
    currency: str = "USD"

    def validate(self) -> "RateCard":
        if not self.license_id or not str(self.license_id).strip():
            raise RoyaltyError("rate card license_id is required")
        if self.model not in RATE_MODELS:
            raise RoyaltyError(f"rate model must be one of {RATE_MODELS}, got {self.model!r}")
        if not isinstance(self.rate, Decimal):
            raise RoyaltyError("rate must be a Decimal")
        if self.rate < 0:
            raise RoyaltyError("rate must be non-negative")
        return self


class UsageLedger:
    """Append-only JSONL ledger of access/usage events."""

    def __init__(self, store_dir: Path | str) -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.store_dir / LEDGER_FILENAME

    def record(
        self,
        asset_id: str,
        consumer_id: str,
        bytes_transferred: int = 0,
        requests: int = 0,
        timestamp: str | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        if not asset_id or not str(asset_id).strip():
            raise RoyaltyError("asset_id is required")
        if not consumer_id or not str(consumer_id).strip():
            raise RoyaltyError("consumer_id is required")
        if bytes_transferred < 0 or requests < 0:
            raise RoyaltyError("bytes_transferred and requests must be >= 0")
        ts = timestamp or utc_now_iso()
        _parse_utc(ts, "timestamp")
        event = {
            "asset_id": asset_id,
            "consumer_id": consumer_id,
            "bytes": int(bytes_transferred),
            "requests": int(requests),
            "ts": ts,
        }
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        append_audit(
            self.store_dir,
            action="usage.record",
            detail=event,
            actor=actor,
        )
        return event

    def read_events(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read events with ``period_start <= ts < period_end`` (both optional)."""
        if not self.ledger_path.exists():
            return []
        start = _parse_utc(period_start, "period_start") if period_start else None
        end = _parse_utc(period_end, "period_end") if period_end else None
        events = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            ts = _parse_utc(event["ts"], "ts")
            if start is not None and ts < start:
                continue
            if end is not None and ts >= end:
                continue
            events.append(event)
        return events


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_CENT, rounding=ROUND_HALF_UP)


def compute_royalty_report(
    ledger: UsageLedger,
    license_store: LicenseStore,
    rate_cards: Iterable[RateCard],
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    """Aggregate usage per licensor/license over a period and price it.

    Events for assets without a license tag, or licenses without a rate card,
    are reported under ``unpriced`` rather than silently dropped. Flat-fee
    licenses are charged once per period when at least one event occurred.
    """
    cards: dict[str, RateCard] = {}
    for card in rate_cards:
        card.validate()
        cards[card.license_id] = card
    events = ledger.read_events(period_start, period_end)

    licensors: dict[str, dict[str, Any]] = {}
    unpriced: list[dict[str, Any]] = []
    currency: str | None = None

    for event in events:
        tag = license_store.latest_tag_for_asset(event["asset_id"])
        if tag is None or tag.license_id not in cards:
            unpriced.append(event)
            continue
        card = cards[tag.license_id]
        if currency is None:
            currency = card.currency
        elif currency != card.currency:
            raise RoyaltyError(
                f"mixed currencies in one report: {currency} vs {card.currency}"
            )
        licensor = licensors.setdefault(
            tag.licensor_id, {"licenses": {}, "total_amount": Decimal("0")}
        )
        bucket = licensor["licenses"].setdefault(
            tag.license_id,
            {
                "model": card.model,
                "rate": str(card.rate),
                "events": 0,
                "bytes": 0,
                "requests": 0,
                "amount": Decimal("0"),
            },
        )
        bucket["events"] += 1
        bucket["bytes"] += event["bytes"]
        bucket["requests"] += event["requests"]

    total = Decimal("0")
    for licensor in licensors.values():
        for license_id, bucket in licensor["licenses"].items():
            card = cards[license_id]
            if card.model == "per_gb":
                amount = _quantize(Decimal(bucket["bytes"]) / BYTES_PER_GB * card.rate)
            elif card.model == "per_request":
                amount = _quantize(Decimal(bucket["requests"]) * card.rate)
            else:
                amount = _quantize(card.rate) if bucket["events"] > 0 else Decimal("0.00")
            bucket["amount"] = str(amount)
            licensor["total_amount"] += amount
        total += licensor["total_amount"]
        licensor["total_amount"] = str(licensor["total_amount"])

    return {
        "schema": "tape-to-cloud/royalty-report/v1",
        "period": {"start": period_start, "end": period_end},
        "generated_at": utc_now_iso(),
        "currency": currency or "USD",
        "licensors": licensors,
        "unpriced_events": len(unpriced),
        "total_amount": str(_quantize(total)),
    }


def render_report_summary(report: dict[str, Any]) -> str:
    """Render a royalty report as a human-readable text summary."""
    lines = [
        "Royalty report",
        f"  period   : {report['period']['start']} .. {report['period']['end']}",
        f"  currency : {report['currency']}",
    ]
    for licensor_id in sorted(report["licensors"]):
        licensor = report["licensors"][licensor_id]
        lines.append(f"  licensor {licensor_id}: {licensor['total_amount']} {report['currency']}")
        for license_id in sorted(licensor["licenses"]):
            bucket = licensor["licenses"][license_id]
            lines.append(
                f"    {license_id} [{bucket['model']} @ {bucket['rate']}]: "
                f"{bucket['events']} events, {bucket['bytes']} bytes, "
                f"{bucket['requests']} requests -> {bucket['amount']}"
            )
    if report["unpriced_events"]:
        lines.append(f"  unpriced events: {report['unpriced_events']}")
    lines.append(f"  TOTAL: {report['total_amount']} {report['currency']}")
    return "\n".join(lines)


__all__ = [
    "BYTES_PER_GB",
    "RATE_MODELS",
    "RateCard",
    "RoyaltyError",
    "UsageLedger",
    "compute_royalty_report",
    "render_report_summary",
]
