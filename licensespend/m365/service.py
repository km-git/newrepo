"""Microsoft 365 subscribed SKUs + user license assignments.

Default path parses fixture JSON. Live Graph is an optional extra
(``msgraph-sdk`` + ``azure-identity``), read-only scopes only.

Honest gap: Graph last-signin lags; treat >90d as unused, not "never".
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from licensespend.privacy import hash_email
from licensespend.seats import Seat, SeatReport, SkuCount

_SKU_MAP = {
    "SPE_E3": "m365-e3",
    "SPE_E5": "m365-e5",
    "ENTERPRISEPACK": "m365-e3",
    "ENTERPRISEPREMIUM": "m365-e5",
    "m365-e3": "m365-e3",
    "m365-e5": "m365-e5",
}


def _parse_date(raw: object) -> date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    text = str(raw)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_sku(raw: str | None) -> str:
    if not raw:
        return "m365-unknown"
    return _SKU_MAP.get(raw, raw)


def parse_subscribed_skus(payload: dict) -> list[SkuCount]:
    rows = payload.get("value") if isinstance(payload.get("value"), list) else payload.get("skus") or []
    out: list[SkuCount] = []
    for row in rows:
        sku = _normalize_sku(row.get("skuPartNumber") or row.get("sku") or row.get("id"))
        prepaid = row.get("prepaidUnits") or {}
        enabled = prepaid.get("enabled") if isinstance(prepaid, dict) else row.get("prepaid")
        out.append(
            SkuCount(
                sku=sku,
                prepaid=int(enabled or row.get("prepaid") or 0),
                consumed=int(row.get("consumedUnits") or row.get("consumed") or 0),
            )
        )
    return out


def parse_users(payload: dict) -> list[Seat]:
    rows = payload.get("users") if isinstance(payload.get("users"), list) else payload.get("value") or []
    seats: list[Seat] = []
    for row in rows:
        user_id = str(row.get("user_id") or row.get("id") or "")
        if not user_id:
            continue
        sku = _normalize_sku(row.get("sku") or row.get("assigned_sku") or _first_assigned_sku(row))
        last_active = _parse_date(
            row.get("last_active")
            or row.get("lastSignInDateTime")
            or (
                (row.get("signInActivity") or {}).get("lastSignInDateTime")
                if isinstance(row.get("signInActivity"), dict)
                else None
            )
        )
        email = row.get("mail") or row.get("email") or row.get("userPrincipalName")
        note = None
        if last_active is None:
            note = "signin unknown (Graph last-signin lag); treat as unused, not never"
        seats.append(
            Seat(
                user_id=user_id,
                sku=sku,
                vendor="microsoft365",
                last_active=last_active,
                department=row.get("department"),
                role="member",
                assigned=True,
                email_hash=hash_email(email) if email else None,
                email=str(email) if email else None,
                note=note,
            )
        )
    return seats


def _first_assigned_sku(row: dict) -> str | None:
    licenses = row.get("assignedLicenses") or []
    if licenses and isinstance(licenses, list):
        first = licenses[0]
        if isinstance(first, dict):
            return first.get("skuId") or first.get("skuPartNumber")
    return None


def load_fixture(fixture_dir: Path) -> SeatReport:
    directory = Path(fixture_dir)
    users_path = directory / "users.json"
    skus_path = directory / "subscribedSkus.json"
    users_payload = _load_json(users_path) if users_path.is_file() else {"users": []}
    skus_payload = _load_json(skus_path) if skus_path.is_file() else {"value": []}
    seats = parse_users(users_payload)
    return SeatReport(
        vendor="microsoft365",
        seats=seats,
        skus=parse_subscribed_skus(skus_payload),
        honest_gap="Graph last-signin lags; treat >90d as unused, not never.",
    )


def load_live() -> SeatReport:
    """Optional live Graph path. Raises if extras are missing."""
    try:
        from azure.identity import DefaultAzureCredential  # type: ignore  # noqa: F401
        from msgraph import GraphServiceClient  # type: ignore  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Install extras: pip install 'licensespend[m365]'") from exc
    raise RuntimeError("Live Graph is optional; use --fixture for the product path")
