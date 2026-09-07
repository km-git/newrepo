"""Unapproved SaaS from SSO catalogs, SPF includes, and expense CSV. No CASB agent."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from licensespend.constants import EXAMPLES
from licensespend.shadow.models import ShadowApp, ShadowReport
from licensespend.usage.service import load_pricebook

_INCLUDE_RE = re.compile(r"include:([^\s]+)")


def _known_vendors() -> set[str]:
    prices = load_pricebook()
    names = {sku.vendor.lower() for sku in prices.values()}
    names.update(sku.id.lower() for sku in prices.values())
    names.update(sku.name.lower() for sku in prices.values())
    return names


def _from_expenses(path: Path) -> list[ShadowApp]:
    if not path.is_file():
        return []
    apps: list[ShadowApp] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            vendor = (row.get("vendor") or "").strip()
            if not vendor:
                continue
            amount = row.get("amount") or row.get("amount_aud") or "0"
            try:
                value = float(amount)
            except ValueError:
                value = 0.0
            apps.append(
                ShadowApp(
                    name=vendor,
                    source="expense-csv",
                    owner=row.get("owner") or None,
                    amount_aud=value,
                    in_pricebook=_is_known(vendor),
                    note=None if _is_known(vendor) else "not in pricebook; possible shadow SaaS",
                )
            )
    return apps


def _is_known(name: str) -> bool:
    blob = name.lower()
    return any(token in blob for token in _known_vendors())


def _from_sso(path: Path) -> list[ShadowApp]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("apps") or payload.get("value") or []
    apps: list[ShadowApp] = []
    for row in rows:
        name = str(row.get("name") or row.get("app") or "")
        if not name:
            continue
        approved = bool(row.get("approved", False))
        apps.append(
            ShadowApp(
                name=name,
                source="sso-catalog",
                owner=row.get("owner"),
                in_pricebook=approved or _is_known(name),
                note=None if approved else "unapproved SSO app",
            )
        )
    return apps


def _from_spf(path: Path) -> list[ShadowApp]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    apps: list[ShadowApp] = []
    for match in _INCLUDE_RE.finditer(text):
        host = match.group(1)
        apps.append(
            ShadowApp(
                name=host,
                source="spf-include",
                in_pricebook=_is_known(host),
                note="DNS heuristic only",
            )
        )
    return apps


def scan(fixture_dir: Path | None = None) -> ShadowReport:
    root = Path(fixture_dir) if fixture_dir else (EXAMPLES / "shadow")
    if root.name != "shadow" and (root / "shadow").is_dir():
        root = root / "shadow"
    apps = _from_expenses(root / "expenses.csv")
    apps.extend(_from_sso(root / "sso_apps.json"))
    apps.extend(_from_spf(root / "spf.txt"))
    return ShadowReport(apps=apps)
