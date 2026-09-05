"""
Monetization Strategy Services — optional broker layer.

A dependency-free (stdlib only) broker that sits on top of any asset catalog and
provides three capabilities from the product blueprint:

  1. License tagging — per-asset license metadata persisted in a manifest.
  2. Access control  — policy decisions (allow/deny + reason) for a principal
     performing an action on an asset given its license class.
  3. Royalty reporting — accrue royalties per license holder from usage events
     using a rate card, aggregated into a report.

Fully deterministic: no network and no implicit clock in the decision logic.
Expiry checks accept an injectable ``now`` for testability.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


STATE_PATH = Path(os.environ.get("EW_MONETIZE_STATE", "output/system/monetize.json"))

LICENSE_TYPES = ("proprietary", "cc-by", "public-domain", "restricted")
DEFAULT_USAGE_RIGHTS = ("read", "train", "redistribute")
# License classes that gate access behind an explicit allow-list.
GATED_LICENSE_TYPES = ("proprietary", "restricted")


def _state_path() -> Path:
  return Path(os.environ.get("EW_MONETIZE_STATE", str(STATE_PATH)))


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
  """Parse an ISO-8601 timestamp; tolerate a trailing ``Z``."""
  if not value:
    return None
  try:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
  except ValueError:
    return None


@dataclass
class LicenseTag:
  """Per-asset license metadata persisted in the manifest."""

  asset_id: str
  license_id: str
  license_type: str = "proprietary"
  holder: str = "unknown"
  terms_url: Optional[str] = None
  usage_rights: List[str] = field(default_factory=lambda: list(DEFAULT_USAGE_RIGHTS))
  allow_list: List[str] = field(default_factory=list)
  issued_at: Optional[str] = None
  expires_at: Optional[str] = None

  def is_expired(self, now: Optional[datetime] = None) -> bool:
    """Whether the license has lapsed relative to an injectable ``now``."""
    exp = _parse_dt(self.expires_at)
    if exp is None:
      return False
    ref = now or datetime.now(timezone.utc)
    if exp.tzinfo is None:
      exp = exp.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
      ref = ref.replace(tzinfo=timezone.utc)
    return ref >= exp

  def to_dict(self) -> Dict[str, Any]:
    return asdict(self)

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> "LicenseTag":
    fields = {
      "asset_id", "license_id", "license_type", "holder", "terms_url",
      "usage_rights", "allow_list", "issued_at", "expires_at",
    }
    return cls(**{k: v for k, v in data.items() if k in fields})


@dataclass
class AccessDecision:
  """Structured result of an access-control check."""

  allowed: bool
  reason: str
  principal: str = ""
  action: str = ""
  asset_id: str = ""

  def to_dict(self) -> Dict[str, Any]:
    return asdict(self)


@dataclass
class UsageEvent:
  """A single recorded use of a tagged asset."""

  asset_id: str
  principal: str
  action: str
  gb: float = 0.0
  revenue: float = 0.0
  timestamp: Optional[str] = None

  def to_dict(self) -> Dict[str, Any]:
    return asdict(self)

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> "UsageEvent":
    fields = {"asset_id", "principal", "action", "gb", "revenue", "timestamp"}
    return cls(**{k: v for k, v in data.items() if k in fields})


@dataclass
class RateCard:
  """Royalty pricing: flat per-access fee, per-GB fee, and revenue share."""

  per_access: float = 0.0
  per_gb: float = 0.0
  revenue_share_pct: float = 0.0

  def royalty_for(self, event: UsageEvent) -> float:
    """Royalty owed for a single usage event under this rate card."""
    fee = self.per_access
    fee += self.per_gb * max(0.0, float(event.gb))
    fee += (self.revenue_share_pct / 100.0) * max(0.0, float(event.revenue))
    return round(fee, 8)

  def to_dict(self) -> Dict[str, Any]:
    return asdict(self)

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> "RateCard":
    fields = {"per_access", "per_gb", "revenue_share_pct"}
    return cls(**{k: v for k, v in data.items() if k in fields})


def evaluate_access(
  tag: LicenseTag,
  principal: str,
  action: str,
  *,
  now: Optional[datetime] = None,
) -> AccessDecision:
  """
  Decide whether ``principal`` may perform ``action`` on the tagged asset.

  Rules (evaluated in order):
    - public-domain licenses allow every action.
    - expired licenses deny (compared against injectable ``now``).
    - the action must appear in the license's ``usage_rights``.
    - proprietary/restricted licenses require the principal in ``allow_list``
      (an empty allow-list denies all principals for those classes).
  """
  def _decision(allowed: bool, reason: str) -> AccessDecision:
    return AccessDecision(
      allowed=allowed,
      reason=reason,
      principal=principal,
      action=action,
      asset_id=tag.asset_id,
    )

  if tag.license_type == "public-domain":
    return _decision(True, "public-domain: all actions permitted")

  if tag.is_expired(now):
    return _decision(False, f"license {tag.license_id} expired at {tag.expires_at}")

  if action not in tag.usage_rights:
    return _decision(False, f"action '{action}' not in usage_rights {tag.usage_rights}")

  if tag.license_type in GATED_LICENSE_TYPES:
    if principal not in tag.allow_list:
      return _decision(
        False,
        f"{tag.license_type} license: principal '{principal}' not in allow-list",
      )
    return _decision(True, f"{tag.license_type} license: principal in allow-list")

  return _decision(True, f"{tag.license_type} license: action '{action}' permitted")


class MonetizationBroker:
  """
  Holds tagged assets + usage events and exposes the broker capabilities.

  State is a JSON manifest round-trippable via the env-configured path
  (``EW_MONETIZE_STATE``, default ``output/system/monetize.json``).
  """

  def __init__(
    self,
    *,
    default_rate_card: Optional[RateCard] = None,
    rate_cards_by_type: Optional[Dict[str, RateCard]] = None,
    rate_cards_by_holder: Optional[Dict[str, RateCard]] = None,
  ) -> None:
    self.tags: Dict[str, LicenseTag] = {}
    self.events: List[UsageEvent] = []
    self.default_rate_card: RateCard = default_rate_card or RateCard()
    self.rate_cards_by_type: Dict[str, RateCard] = dict(rate_cards_by_type or {})
    self.rate_cards_by_holder: Dict[str, RateCard] = dict(rate_cards_by_holder or {})

  # --- License tagging ---------------------------------------------------

  def tag_asset(self, tag: LicenseTag) -> LicenseTag:
    """Persist (in memory) a license tag for an asset and return it."""
    self.tags[tag.asset_id] = tag
    return tag

  def get_license(self, asset_id: str) -> Optional[LicenseTag]:
    """Look up an asset's license tag, or ``None`` if untagged."""
    return self.tags.get(asset_id)

  # --- Access control ----------------------------------------------------

  def check_access(
    self,
    principal: str,
    action: str,
    asset_id: str,
    *,
    now: Optional[datetime] = None,
  ) -> AccessDecision:
    """Policy decision for a principal/action/asset triple."""
    tag = self.get_license(asset_id)
    if tag is None:
      return AccessDecision(
        allowed=False,
        reason=f"asset '{asset_id}' has no license tag",
        principal=principal,
        action=action,
        asset_id=asset_id,
      )
    return evaluate_access(tag, principal, action, now=now)

  # --- Royalty reporting -------------------------------------------------

  def record_usage(
    self,
    asset_id: str,
    principal: str,
    action: str,
    *,
    gb: float = 0.0,
    revenue: float = 0.0,
    timestamp: Optional[str] = None,
  ) -> UsageEvent:
    """Record a usage event against a (tagged or untagged) asset."""
    event = UsageEvent(
      asset_id=asset_id,
      principal=principal,
      action=action,
      gb=float(gb),
      revenue=float(revenue),
      timestamp=timestamp,
    )
    self.events.append(event)
    return event

  def rate_card_for(self, tag: Optional[LicenseTag]) -> RateCard:
    """
    Resolve the applicable rate card, most specific first:
    per-holder, then per-license-type, then the default.
    """
    if tag is not None:
      if tag.holder in self.rate_cards_by_holder:
        return self.rate_cards_by_holder[tag.holder]
      if tag.license_type in self.rate_cards_by_type:
        return self.rate_cards_by_type[tag.license_type]
    return self.default_rate_card

  def royalty_report(self) -> Dict[str, Any]:
    """
    Aggregate royalties per license holder from all recorded usage events.

    Returns totals per holder with a per-asset breakdown, event counts,
    total GB moved, and total fees.
    """
    holders: Dict[str, Dict[str, Any]] = {}
    grand_total = 0.0

    for event in self.events:
      tag = self.get_license(event.asset_id)
      holder = tag.holder if tag is not None else "unlicensed"
      rate = self.rate_card_for(tag)
      fee = rate.royalty_for(event)
      grand_total += fee

      hrec = holders.setdefault(holder, {
        "holder": holder,
        "total_fees": 0.0,
        "event_count": 0,
        "total_gb": 0.0,
        "total_revenue": 0.0,
        "assets": {},
      })
      hrec["total_fees"] = round(hrec["total_fees"] + fee, 8)
      hrec["event_count"] += 1
      hrec["total_gb"] = round(hrec["total_gb"] + max(0.0, float(event.gb)), 8)
      hrec["total_revenue"] = round(hrec["total_revenue"] + max(0.0, float(event.revenue)), 8)

      arec = hrec["assets"].setdefault(event.asset_id, {
        "asset_id": event.asset_id,
        "fees": 0.0,
        "event_count": 0,
        "gb": 0.0,
      })
      arec["fees"] = round(arec["fees"] + fee, 8)
      arec["event_count"] += 1
      arec["gb"] = round(arec["gb"] + max(0.0, float(event.gb)), 8)

    for hrec in holders.values():
      hrec["assets"] = sorted(hrec["assets"].values(), key=lambda a: a["asset_id"])

    return {
      "generated_at": datetime.now(timezone.utc).isoformat(),
      "grand_total_fees": round(grand_total, 8),
      "event_count": len(self.events),
      "holders": sorted(holders.values(), key=lambda h: -h["total_fees"]),
    }

  # --- Persistence -------------------------------------------------------

  def to_dict(self) -> Dict[str, Any]:
    return {
      "tags": [t.to_dict() for t in self.tags.values()],
      "events": [e.to_dict() for e in self.events],
      "default_rate_card": self.default_rate_card.to_dict(),
      "rate_cards_by_type": {k: v.to_dict() for k, v in self.rate_cards_by_type.items()},
      "rate_cards_by_holder": {k: v.to_dict() for k, v in self.rate_cards_by_holder.items()},
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> "MonetizationBroker":
    broker = cls(
      default_rate_card=RateCard.from_dict(data.get("default_rate_card") or {}),
      rate_cards_by_type={
        k: RateCard.from_dict(v) for k, v in (data.get("rate_cards_by_type") or {}).items()
      },
      rate_cards_by_holder={
        k: RateCard.from_dict(v) for k, v in (data.get("rate_cards_by_holder") or {}).items()
      },
    )
    for t in data.get("tags", []):
      tag = LicenseTag.from_dict(t)
      broker.tags[tag.asset_id] = tag
    for e in data.get("events", []):
      broker.events.append(UsageEvent.from_dict(e))
    return broker

  def save(self, path: Optional[Path] = None) -> Path:
    """Persist the manifest to the env-configured JSON path (or ``path``)."""
    target = Path(path) if path is not None else _state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(self.to_dict(), indent=2, default=str), encoding="utf-8")
    return target

  @classmethod
  def load(cls, path: Optional[Path] = None) -> "MonetizationBroker":
    """Load a manifest from the env-configured JSON path (or ``path``)."""
    target = Path(path) if path is not None else _state_path()
    if not target.exists():
      return cls()
    try:
      data = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
      return cls()
    return cls.from_dict(data)


# --- Module-level convenience -------------------------------------------


def tag_asset(broker: MonetizationBroker, **kwargs: Any) -> LicenseTag:
  """Build a :class:`LicenseTag` from kwargs and register it on ``broker``."""
  return broker.tag_asset(LicenseTag(**kwargs))


def check_access(
  broker: MonetizationBroker,
  principal: str,
  action: str,
  asset_id: str,
  *,
  now: Optional[datetime] = None,
) -> AccessDecision:
  """Thin wrapper over :meth:`MonetizationBroker.check_access`."""
  return broker.check_access(principal, action, asset_id, now=now)


def run_monetize_demo() -> Dict[str, Any]:
  """
  Build a tiny in-memory example and return its royalty report.

  Deterministic and self-contained — no I/O, network, or persistence.
  """
  broker = MonetizationBroker(
    default_rate_card=RateCard(per_access=0.01, per_gb=0.10),
    rate_cards_by_type={
      "proprietary": RateCard(per_access=1.0, per_gb=0.50, revenue_share_pct=10.0),
    },
  )
  broker.tag_asset(LicenseTag(
    asset_id="tape-001",
    license_id="LIC-PROP-1",
    license_type="proprietary",
    holder="AcmeArchives",
    usage_rights=["read", "train"],
    allow_list=["research-team"],
  ))
  broker.tag_asset(LicenseTag(
    asset_id="tape-002",
    license_id="LIC-PD-1",
    license_type="public-domain",
    holder="PublicTrust",
    usage_rights=["read", "train", "redistribute"],
  ))

  broker.record_usage("tape-001", "research-team", "train", gb=4.0, revenue=100.0)
  broker.record_usage("tape-002", "anyone", "redistribute", gb=2.0)

  return {
    "access_allowed": broker.check_access("research-team", "train", "tape-001").to_dict(),
    "access_denied": broker.check_access("outsider", "train", "tape-001").to_dict(),
    "royalty_report": broker.royalty_report(),
  }
