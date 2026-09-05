"""
Monetization Strategy Services — license/API-key management, usage metering,
and royalty/revenue reporting for the Elliott Wave trading analysis tool.

Tier model
----------
free        Single symbol, 1h timeframe only, no export.
pro         All timeframes, batch up to 10 symbols, export CSV.
enterprise  Unlimited, all features, API-key management, usage reports.

Environment variables
---------------------
EW_TIER=free|pro|enterprise   (default: free)
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Tier definition
# ---------------------------------------------------------------------------

class MonetizationTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    @property
    def rank(self) -> int:
        return {self.FREE: 0, self.PRO: 1, self.ENTERPRISE: 2}[self]

    def __ge__(self, other: "MonetizationTier") -> bool:  # type: ignore[override]
        return self.rank >= other.rank

    def __gt__(self, other: "MonetizationTier") -> bool:  # type: ignore[override]
        return self.rank > other.rank

    def __le__(self, other: "MonetizationTier") -> bool:  # type: ignore[override]
        return self.rank <= other.rank

    def __lt__(self, other: "MonetizationTier") -> bool:  # type: ignore[override]
        return self.rank < other.rank


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AccessDeniedError(PermissionError):
    """Raised when the current tier does not permit a requested feature."""

    def __init__(self, feature: str, current: MonetizationTier, required: MonetizationTier) -> None:
        self.feature = feature
        self.current = current
        self.required = required
        super().__init__(
            f"Feature '{feature}' requires tier '{required.value}'; "
            f"current tier is '{current.value}'. "
            f"Set EW_TIER={required.value} to unlock."
        )


# ---------------------------------------------------------------------------
# Feature gate map — feature_name → minimum tier required
# ---------------------------------------------------------------------------

FEATURE_GATES: Dict[str, MonetizationTier] = {
    # Free tier
    "analyze_single": MonetizationTier.FREE,
    "timeframe_1h": MonetizationTier.FREE,
    "cache": MonetizationTier.FREE,
    "health": MonetizationTier.FREE,
    # Pro tier
    "all_timeframes": MonetizationTier.PRO,
    "batch_10": MonetizationTier.PRO,
    "export_csv": MonetizationTier.PRO,
    "paper_forward": MonetizationTier.PRO,
    "effectiveness": MonetizationTier.PRO,
    "goal_mode": MonetizationTier.PRO,
    "autoresearch": MonetizationTier.PRO,
    # Enterprise tier
    "batch_unlimited": MonetizationTier.ENTERPRISE,
    "api_key_management": MonetizationTier.ENTERPRISE,
    "usage_reports": MonetizationTier.ENTERPRISE,
    "revenue_reports": MonetizationTier.ENTERPRISE,
    "v6_scanner": MonetizationTier.ENTERPRISE,
    "autonomous_daily": MonetizationTier.ENTERPRISE,
    "execute_live": MonetizationTier.ENTERPRISE,
    "executive_intel": MonetizationTier.ENTERPRISE,
}

# Human-readable feature descriptions for --monetize-status
FEATURE_DESCRIPTIONS: Dict[str, str] = {
    "analyze_single": "Analyze a single symbol",
    "timeframe_1h": "1h timeframe analysis",
    "cache": "On-disk analysis cache",
    "health": "System health checks",
    "all_timeframes": "All timeframes (15m, 4h, 12h, 1d, 1w, …)",
    "batch_10": "Batch analysis (up to 10 symbols)",
    "export_csv": "Export results to CSV",
    "paper_forward": "Paper forward simulation",
    "effectiveness": "Effectiveness validation",
    "goal_mode": "Autonomous goal-mode cycle",
    "autoresearch": "AutoResearch batch",
    "batch_unlimited": "Unlimited batch analysis",
    "api_key_management": "API key / client provisioning",
    "usage_reports": "Usage metering reports",
    "revenue_reports": "Revenue / royalty reports",
    "v6_scanner": "V6 universe scanner (1 000 pairs × 6 TFs)",
    "autonomous_daily": "24 h autonomous operations daemon",
    "execute_live": "Live order execution via broker",
    "executive_intel": "Executive intelligence dashboard",
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_USAGE_LOG_PATH = Path(
    os.environ.get("EW_USAGE_LOG", "output/system/usage_log.jsonl")
)


# ---------------------------------------------------------------------------
# Core service
# ---------------------------------------------------------------------------

class MonetizationService:
    """Central monetization service — tier detection, access gating, usage metering."""

    def __init__(
        self,
        tier: Optional[MonetizationTier] = None,
        usage_log_path: Optional[Path] = None,
    ) -> None:
        self._tier = tier
        self._log_path = usage_log_path or _USAGE_LOG_PATH

    # ------------------------------------------------------------------
    # Tier
    # ------------------------------------------------------------------

    def get_tier(self) -> MonetizationTier:
        """Read current tier from EW_TIER env var (or constructor override)."""
        if self._tier is not None:
            return self._tier
        raw = os.environ.get("EW_TIER", "free").strip().lower()
        try:
            return MonetizationTier(raw)
        except ValueError:
            return MonetizationTier.FREE

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------

    def check_access(self, feature: str) -> bool:
        """
        Return True if the current tier permits *feature*.
        Raises AccessDeniedError otherwise.
        Unknown features are treated as FREE-tier (permitted by all).
        """
        required = FEATURE_GATES.get(feature, MonetizationTier.FREE)
        current = self.get_tier()
        if current >= required:
            return True
        raise AccessDeniedError(feature, current, required)

    def has_access(self, feature: str) -> bool:
        """Non-raising variant; returns bool without raising."""
        try:
            return self.check_access(feature)
        except AccessDeniedError:
            return False

    def available_features(self) -> List[str]:
        """Return sorted list of feature names available at the current tier."""
        tier = self.get_tier()
        return sorted(
            f for f, req in FEATURE_GATES.items() if tier >= req
        )

    def locked_features(self) -> List[str]:
        """Return sorted list of feature names locked at the current tier."""
        tier = self.get_tier()
        return sorted(
            f for f, req in FEATURE_GATES.items() if tier < req
        )

    # ------------------------------------------------------------------
    # Usage metering
    # ------------------------------------------------------------------

    def log_usage(
        self,
        symbol: str,
        timeframe: str,
        feature: str,
        tokens_used: int = 0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a usage record to the JSONL usage log."""
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        record: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tier": self.get_tier().value,
            "symbol": symbol,
            "timeframe": timeframe,
            "feature": feature,
            "tokens_used": int(tokens_used),
        }
        if extra:
            record.update(extra)
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    # ------------------------------------------------------------------
    # Usage report
    # ------------------------------------------------------------------

    def usage_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Read the usage log and return a summary dict aggregated by
        tier / feature / symbol for the past *days* days.
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        records: List[Dict[str, Any]] = []

        if self._log_path.exists():
            with open(self._log_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        ts = datetime.fromisoformat(rec.get("ts", ""))
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        if ts >= cutoff:
                            records.append(rec)
                    except Exception:
                        continue

        by_tier: Dict[str, int] = defaultdict(int)
        by_feature: Dict[str, int] = defaultdict(int)
        by_symbol: Dict[str, int] = defaultdict(int)
        total_tokens = 0

        for rec in records:
            by_tier[rec.get("tier", "unknown")] += 1
            by_feature[rec.get("feature", "unknown")] += 1
            by_symbol[rec.get("symbol", "unknown")] += 1
            total_tokens += int(rec.get("tokens_used", 0))

        return {
            "report_days": days,
            "total_calls": len(records),
            "total_tokens_used": total_tokens,
            "by_tier": dict(by_tier),
            "by_feature": dict(by_feature),
            "by_symbol": dict(by_symbol),
            "log_path": str(self._log_path),
        }

    # ------------------------------------------------------------------
    # Revenue estimate
    # ------------------------------------------------------------------

    def revenue_estimate(
        self,
        pro_price_usd: float = 29.0,
        enterprise_price_usd: float = 299.0,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Toy revenue model: count distinct active users per tier from usage
        logs, multiply by monthly seat price.

        Since we only have call records (not user IDs), we treat each unique
        (tier, symbol) pair as a proxy for an active subscription seat.
        """
        report = self.usage_report(days=days)
        by_tier = report["by_tier"]

        pro_calls = by_tier.get("pro", 0)
        enterprise_calls = by_tier.get("enterprise", 0)

        # Heuristic: assume one seat per 100 calls (floor 1 if any calls).
        pro_seats = max(1, pro_calls // 100) if pro_calls else 0
        enterprise_seats = max(1, enterprise_calls // 100) if enterprise_calls else 0

        pro_mrr = pro_seats * pro_price_usd
        enterprise_mrr = enterprise_seats * enterprise_price_usd
        total_mrr = pro_mrr + enterprise_mrr

        return {
            "period_days": days,
            "pro_price_usd": pro_price_usd,
            "enterprise_price_usd": enterprise_price_usd,
            "pro_calls": pro_calls,
            "enterprise_calls": enterprise_calls,
            "estimated_pro_seats": pro_seats,
            "estimated_enterprise_seats": enterprise_seats,
            "estimated_pro_mrr_usd": round(pro_mrr, 2),
            "estimated_enterprise_mrr_usd": round(enterprise_mrr, 2),
            "estimated_total_mrr_usd": round(total_mrr, 2),
            "estimated_arr_usd": round(total_mrr * 12, 2),
            "note": (
                "Toy revenue model: seats ≈ calls / 100; "
                "replace with real subscriber records for production."
            ),
        }

    # ------------------------------------------------------------------
    # Status summary
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return a full status dict suitable for --monetize-status."""
        tier = self.get_tier()
        available = self.available_features()
        locked = self.locked_features()

        available_detail = {
            f: FEATURE_DESCRIPTIONS.get(f, f) for f in available
        }
        locked_detail = {
            f: {
                "description": FEATURE_DESCRIPTIONS.get(f, f),
                "requires": FEATURE_GATES[f].value,
            }
            for f in locked
        }

        return {
            "current_tier": tier.value,
            "tier_rank": tier.rank,
            "all_tiers": [t.value for t in MonetizationTier],
            "available_features": available_detail,
            "locked_features": locked_detail,
            "env_var": "EW_TIER",
            "usage_log": str(self._log_path),
        }


# ---------------------------------------------------------------------------
# Module-level convenience singleton
# ---------------------------------------------------------------------------

_service: Optional[MonetizationService] = None


def get_service() -> MonetizationService:
    """Return the process-level MonetizationService singleton."""
    global _service
    if _service is None:
        _service = MonetizationService()
    return _service


def get_tier() -> MonetizationTier:
    return get_service().get_tier()


def check_access(feature: str) -> bool:
    return get_service().check_access(feature)


def has_access(feature: str) -> bool:
    return get_service().has_access(feature)


def log_usage(
    symbol: str,
    timeframe: str,
    feature: str,
    tokens_used: int = 0,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    get_service().log_usage(symbol, timeframe, feature, tokens_used, extra)


def usage_report(days: int = 30) -> Dict[str, Any]:
    return get_service().usage_report(days=days)


def revenue_estimate(
    pro_price_usd: float = 29.0,
    enterprise_price_usd: float = 299.0,
    days: int = 30,
) -> Dict[str, Any]:
    return get_service().revenue_estimate(
        pro_price_usd=pro_price_usd,
        enterprise_price_usd=enterprise_price_usd,
        days=days,
    )


def monetize_status() -> Dict[str, Any]:
    return get_service().status()
