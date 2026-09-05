"""
Monetization Strategy Services — license tagging, access control, royalty reporting.

Tier definitions
----------------
free       : single-symbol analysis only; no batch, no live execution, no brain/OKF
pro        : batch up to 50 symbols, paper execution, brain/OKF, effectiveness validation
enterprise : unlimited batch, live execution, v6 scanner, autonomous daily ops, all features

Environment
-----------
EW_LICENSE_TIER : "free" | "pro" | "enterprise"  (default "free")

Usage
-----
    from engine.monetize import AccessController, LicenseTagger, RoyaltyReporter

    ac = AccessController()
    if ac.can("batch"):
        ...
    LicenseTagger.tag(analysis_dict)
    RoyaltyReporter().record_setup("BTC/USDT").save()
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Literal, Optional

# ---------------------------------------------------------------------------
# Tier type
# ---------------------------------------------------------------------------

Tier = Literal["free", "pro", "enterprise"]

TIERS: tuple[Tier, ...] = ("free", "pro", "enterprise")

# ---------------------------------------------------------------------------
# Feature matrix
# ---------------------------------------------------------------------------

#: Features available at each tier (additive — each tier inherits lower tiers).
_TIER_FEATURES: Dict[str, FrozenSet[str]] = {
    "free": frozenset({
        "single_symbol",
        "cache",
        "llm_advisory",
    }),
    "pro": frozenset({
        "single_symbol",
        "cache",
        "llm_advisory",
        "batch",
        "paper_execution",
        "brain_okf",
        "effectiveness_validation",
        "gap_audit",
        "autoresearch",
        "goal_mode",
        "outcome_tracking",
        "tv_oss",
    }),
    "enterprise": frozenset({
        "single_symbol",
        "cache",
        "llm_advisory",
        "batch",
        "paper_execution",
        "brain_okf",
        "effectiveness_validation",
        "gap_audit",
        "autoresearch",
        "goal_mode",
        "outcome_tracking",
        "tv_oss",
        "live_execution",
        "v6_scanner",
        "autonomous_daily",
        "unlimited_batch",
        "e2e_cycle",
        "universe_scanner",
        "pr_agent",
    }),
}

#: Human-readable description for each feature.
FEATURE_DESCRIPTIONS: Dict[str, str] = {
    "single_symbol":          "Single-symbol Elliott Wave + harmonic analysis",
    "cache":                  "On-disk OHLCV and semantic cache",
    "llm_advisory":           "Multi-model LLM advisory panel (read-only)",
    "batch":                  "Batch analysis up to 50 symbols",
    "paper_execution":        "Paper (simulated) order execution",
    "brain_okf":              "OKF secondary brain + self-improvement loop",
    "effectiveness_validation": "Effectiveness validation + walk-forward testing",
    "gap_audit":              "Resource gap audit (self-challenge)",
    "autoresearch":           "Nightly AutoResearch + goal-mode runs",
    "goal_mode":              "Goal-mode multi-step planning cycles",
    "outcome_tracking":       "Setup outcome tracking + performance metrics",
    "tv_oss":                 "TradingView OSS indicator consensus",
    "live_execution":         "Live order execution via Kraken API",
    "v6_scanner":             "V6 universe scanner (1 000 pairs × 6 TFs)",
    "autonomous_daily":       "24/7 autonomous daily ops daemon",
    "unlimited_batch":        "Unlimited batch size (all pairs)",
    "e2e_cycle":              "End-to-end continuous-improvement cycle",
    "universe_scanner":       "Universe scanner (overlapping 24/7 chunks)",
    "pr_agent":               "PR executive consensus + auto-approve/merge",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_tier(tier: Optional[str] = None) -> Tier:
    """Return a validated tier, reading EW_LICENSE_TIER env var when *tier* is None."""
    raw = (tier or os.environ.get("EW_LICENSE_TIER", "free")).lower().strip()
    if raw not in TIERS:
        raw = "free"
    return raw  # type: ignore[return-value]


def features_for_tier(tier: Optional[str] = None) -> FrozenSet[str]:
    """Return the set of feature keys available for *tier*."""
    return _TIER_FEATURES[_resolve_tier(tier)]


# ---------------------------------------------------------------------------
# LicenseTagger
# ---------------------------------------------------------------------------

class LicenseTagger:
    """Attach license metadata to any analysis output dict (in-place + return)."""

    @staticmethod
    def tag(
        payload: Dict[str, Any],
        *,
        tier: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Inject a ``_license`` key into *payload* and return it.

        Args:
            payload: The analysis dict to tag (modified in-place).
            tier:    Override tier; falls back to ``EW_LICENSE_TIER`` env var.
            extra:   Additional metadata merged into the license block.

        Returns:
            The same *payload* dict, now containing ``_license``.
        """
        resolved = _resolve_tier(tier)
        block: Dict[str, Any] = {
            "tier": resolved,
            "features": sorted(features_for_tier(resolved)),
            "tagged_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            block.update(extra)
        payload["_license"] = block
        return payload

    @staticmethod
    def strip(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Remove the ``_license`` key from *payload* (in-place + return)."""
        payload.pop("_license", None)
        return payload

    @staticmethod
    def read(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return the ``_license`` block from *payload*, or None."""
        return payload.get("_license")


# ---------------------------------------------------------------------------
# AccessController
# ---------------------------------------------------------------------------

class AccessController:
    """Enforce feature access according to the active license tier.

    Args:
        tier: Override tier; falls back to ``EW_LICENSE_TIER`` env var.

    Examples::

        ac = AccessController()
        if not ac.can("batch"):
            raise PermissionError("Batch requires pro or enterprise tier")
        ac.require("live_execution")  # raises AccessDeniedError if denied
    """

    class AccessDeniedError(PermissionError):
        """Raised by :meth:`require` when a feature is not available."""

    def __init__(self, tier: Optional[str] = None) -> None:
        self._tier: Tier = _resolve_tier(tier)
        self._features: FrozenSet[str] = _TIER_FEATURES[self._tier]

    # ------------------------------------------------------------------
    @property
    def tier(self) -> Tier:
        return self._tier

    @property
    def features(self) -> FrozenSet[str]:
        return self._features

    # ------------------------------------------------------------------
    def can(self, feature: str) -> bool:
        """Return True if *feature* is available on the current tier."""
        return feature in self._features

    def require(self, feature: str) -> None:
        """Raise :class:`AccessDeniedError` when *feature* is not available.

        Args:
            feature: Feature key to check.

        Raises:
            AccessDeniedError: When the tier does not include *feature*.
        """
        if not self.can(feature):
            min_tier = self._minimum_tier_for(feature)
            msg = (
                f"Feature '{feature}' is not available on the '{self._tier}' tier."
            )
            if min_tier:
                msg += f" Requires '{min_tier}' or higher."
            raise self.AccessDeniedError(msg)

    def denied_features(self) -> List[str]:
        """Return all features *not* available on this tier."""
        all_features: FrozenSet[str] = _TIER_FEATURES["enterprise"]
        return sorted(all_features - self._features)

    def access_matrix(self) -> Dict[str, Any]:
        """Return a serialisable dict with tier, allowed, and denied feature lists."""
        return {
            "tier": self._tier,
            "allowed": sorted(self._features),
            "denied": self.denied_features(),
            "descriptions": {
                k: FEATURE_DESCRIPTIONS.get(k, k)
                for k in sorted(_TIER_FEATURES["enterprise"])
            },
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _minimum_tier_for(feature: str) -> Optional[Tier]:
        """Return the cheapest tier that includes *feature*, or None."""
        for t in TIERS:
            if feature in _TIER_FEATURES[t]:
                return t
        return None


# ---------------------------------------------------------------------------
# RoyaltyReporter
# ---------------------------------------------------------------------------

_ROYALTY_PATH = Path(
    os.environ.get("EW_ROYALTY_REPORT_PATH", "output/system/royalty_report.json")
)


class RoyaltyReporter:
    """Accumulate usage metrics for SaaS metering / billing integration.

    Each call to :meth:`record_setup`, :meth:`record_signal`, or
    :meth:`record_ticker` increments the in-memory counters.  Call
    :meth:`save` to persist (or merge) with ``output/system/royalty_report.json``.

    Args:
        tier:        Override tier; falls back to ``EW_LICENSE_TIER`` env var.
        report_path: Override output path (defaults to ``EW_ROYALTY_REPORT_PATH``
                     or ``output/system/royalty_report.json``).

    Example::

        rr = RoyaltyReporter()
        rr.record_setup("BTC/USDT").record_signal("BTC/USDT", "SHORT")
        rr.record_tickers(["BTC/USDT", "ETH/USDT"])
        rr.save()
        print(rr.report())
    """

    def __init__(
        self,
        tier: Optional[str] = None,
        report_path: Optional[Path] = None,
    ) -> None:
        self._tier: Tier = _resolve_tier(tier)
        self._path: Path = report_path or _ROYALTY_PATH
        self._setups: List[str] = []
        self._signals: List[Dict[str, str]] = []
        self._tickers: List[str] = []

    # ------------------------------------------------------------------
    def record_setup(self, symbol: str) -> "RoyaltyReporter":
        """Record one analysis setup event for *symbol*."""
        self._setups.append(symbol)
        return self

    def record_signal(self, symbol: str, direction: str = "") -> "RoyaltyReporter":
        """Record one signal fired (e.g. entry/exit signal)."""
        self._signals.append({"symbol": symbol, "direction": direction})
        return self

    def record_ticker(self, symbol: str) -> "RoyaltyReporter":
        """Record one ticker scanned."""
        self._tickers.append(symbol)
        return self

    def record_tickers(self, symbols: List[str]) -> "RoyaltyReporter":
        """Record multiple tickers scanned in a single call."""
        self._tickers.extend(symbols)
        return self

    # ------------------------------------------------------------------
    def report(self) -> Dict[str, Any]:
        """Return the current usage report as a plain dict (not persisted)."""
        return {
            "tier": self._tier,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "usage": {
                "setups_generated": len(self._setups),
                "signals_fired": len(self._signals),
                "tickers_scanned": len(self._tickers),
            },
            "detail": {
                "setups": self._setups,
                "signals": self._signals,
                "tickers": sorted(set(self._tickers)),
            },
        }

    def save(self, *, merge: bool = True) -> Path:
        """Persist (or merge) the current report to disk.

        When *merge* is True (default) and an existing report exists on disk,
        counters from both are summed so the file acts as a running total.

        Args:
            merge: Whether to merge with an existing on-disk report.

        Returns:
            Path to the saved file.
        """
        current = self.report()

        if merge and self._path.exists():
            try:
                existing: Dict[str, Any] = json.loads(self._path.read_text())
                ex_usage = existing.get("usage", {})
                current["usage"]["setups_generated"] += ex_usage.get("setups_generated", 0)
                current["usage"]["signals_fired"] += ex_usage.get("signals_fired", 0)
                current["usage"]["tickers_scanned"] += ex_usage.get("tickers_scanned", 0)
                # Merge detail lists
                current["detail"]["setups"] = (
                    existing.get("detail", {}).get("setups", []) + current["detail"]["setups"]
                )
                current["detail"]["signals"] = (
                    existing.get("detail", {}).get("signals", []) + current["detail"]["signals"]
                )
                combined_tickers = list(
                    set(existing.get("detail", {}).get("tickers", []))
                    | set(current["detail"]["tickers"])
                )
                current["detail"]["tickers"] = sorted(combined_tickers)
            except (json.JSONDecodeError, KeyError):
                pass

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(current, indent=2, default=str))
        return self._path

    @classmethod
    def load(cls, report_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load and return the persisted report dict (empty dict if none exists)."""
        path = report_path or _ROYALTY_PATH
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}


# ---------------------------------------------------------------------------
# Module-level convenience helpers
# ---------------------------------------------------------------------------

def monetize_status(tier: Optional[str] = None) -> Dict[str, Any]:
    """Return a combined status dict: tier, access matrix, and saved royalty report."""
    ac = AccessController(tier=tier)
    return {
        "license": ac.access_matrix(),
        "royalty_report": RoyaltyReporter.load(),
    }
