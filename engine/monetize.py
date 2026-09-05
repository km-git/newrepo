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
from typing import Any, Dict, FrozenSet, Iterable, List, Literal, Optional

# ---------------------------------------------------------------------------
# Tier type
# ---------------------------------------------------------------------------

Tier = Literal["free", "pro", "enterprise"]

TIERS: tuple[Tier, ...] = ("free", "pro", "enterprise")

#: Pro-tier batch cap (enterprise unlocks ``unlimited_batch``).
PRO_BATCH_LIMIT = 50

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

def raw_env_tier() -> str:
    """Return the raw ``EW_LICENSE_TIER`` value (default ``free``)."""
    return os.environ.get("EW_LICENSE_TIER", "free")


def env_tier_is_valid(raw: Optional[str] = None) -> bool:
    """Return True when *raw* (or the env var) is a known tier."""
    value = (raw if raw is not None else raw_env_tier()).lower().strip()
    return value in TIERS


def env_tier_warning() -> Optional[str]:
    """Return a warning when ``EW_LICENSE_TIER`` is set but invalid, else None."""
    if "EW_LICENSE_TIER" not in os.environ:
        return None
    raw = os.environ.get("EW_LICENSE_TIER", "")
    if env_tier_is_valid(raw):
        return None
    return (
        f"EW_LICENSE_TIER={raw!r} is invalid; using 'free'. "
        f"Valid: {', '.join(TIERS)}"
    )


def _resolve_tier(tier: Optional[str] = None) -> Tier:
    """Return a validated tier, reading EW_LICENSE_TIER env var when *tier* is None.

    Unknown values fail safe to ``free`` so access gates stay conservative.
    """
    raw = (tier if tier is not None else raw_env_tier()).lower().strip()
    if raw not in TIERS:
        raw = "free"
    return raw  # type: ignore[return-value]


def features_for_tier(tier: Optional[str] = None) -> FrozenSet[str]:
    """Return the set of feature keys available for *tier*."""
    return _TIER_FEATURES[_resolve_tier(tier)]


def known_features() -> FrozenSet[str]:
    """Return every feature key defined on the enterprise matrix."""
    return _TIER_FEATURES["enterprise"]


def max_batch_size(tier: Optional[str] = None) -> Optional[int]:
    """Return the batch-size cap for *tier*, or None when unlimited."""
    resolved = _resolve_tier(tier)
    if resolved == "free":
        return 1
    if resolved == "pro":
        return PRO_BATCH_LIMIT
    return None


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

        Raises:
            TypeError: When *payload* is not a dict.
        """
        if not isinstance(payload, dict):
            raise TypeError(
                f"LicenseTagger.tag expects a dict, got {type(payload).__name__}"
            )
        resolved = _resolve_tier(tier)
        block: Dict[str, Any] = {
            "tier": resolved,
            "features": sorted(features_for_tier(resolved)),
            "tagged_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            for key, value in extra.items():
                if key not in ("tier", "features", "tagged_at"):
                    block[key] = value
        payload["_license"] = block
        return payload

    @staticmethod
    def strip(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Remove the ``_license`` key from *payload* (in-place + return)."""
        if not isinstance(payload, dict):
            return payload
        payload.pop("_license", None)
        return payload

    @staticmethod
    def read(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return the ``_license`` block from *payload*, or None."""
        if not isinstance(payload, dict):
            return None
        block = payload.get("_license")
        return block if isinstance(block, dict) else None


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
            if min_tier is None:
                msg = f"Feature '{feature}' is not a recognized monetize feature."
            else:
                msg = (
                    f"Feature '{feature}' is not available on the '{self._tier}' tier."
                    f" Requires '{min_tier}' or higher."
                )
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

def _default_royalty_path() -> Path:
    """Resolve the royalty report path from env (evaluated at call time)."""
    return Path(os.environ.get("EW_ROYALTY_REPORT_PATH", "output/system/royalty_report.json"))


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
        self._path: Path = Path(report_path) if report_path is not None else _default_royalty_path()
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
        self._path.parent.mkdir(parents=True, exist_ok=True)

        def _merge_and_write() -> Dict[str, Any]:
            current = self.report()
            if merge and self._path.exists():
                try:
                    existing: Dict[str, Any] = json.loads(self._path.read_text())
                    ex_usage = existing.get("usage", {})
                    current["usage"]["setups_generated"] += int(ex_usage.get("setups_generated", 0) or 0)
                    current["usage"]["signals_fired"] += int(ex_usage.get("signals_fired", 0) or 0)
                    current["usage"]["tickers_scanned"] += int(ex_usage.get("tickers_scanned", 0) or 0)
                    current["detail"]["setups"] = (
                        list(existing.get("detail", {}).get("setups", []) or [])
                        + current["detail"]["setups"]
                    )
                    current["detail"]["signals"] = (
                        list(existing.get("detail", {}).get("signals", []) or [])
                        + current["detail"]["signals"]
                    )
                    combined_tickers = list(
                        set(existing.get("detail", {}).get("tickers", []) or [])
                        | set(current["detail"]["tickers"])
                    )
                    current["detail"]["tickers"] = sorted(combined_tickers)
                except (json.JSONDecodeError, KeyError, TypeError, OSError, ValueError):
                    pass
            self._path.write_text(json.dumps(current, indent=2, default=str))
            return current

        lock_path = self._path.with_name(self._path.name + ".lock")
        try:
            import fcntl

            with lock_path.open("a+") as lockf:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
                try:
                    _merge_and_write()
                finally:
                    fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError):
            _merge_and_write()
        return self._path

    @classmethod
    def load(cls, report_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load and return the persisted report dict (empty dict if none exists)."""
        path = Path(report_path) if report_path is not None else _default_royalty_path()
        if not path.exists():
            return {}
        try:
            loaded = json.loads(path.read_text())
            return loaded if isinstance(loaded, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}


# ---------------------------------------------------------------------------
# Module-level convenience helpers
# ---------------------------------------------------------------------------

def monetize_status(tier: Optional[str] = None) -> Dict[str, Any]:
    """Return a combined status dict: tier, access matrix, and saved royalty report."""
    ac = AccessController(tier=tier)
    raw = raw_env_tier()
    status: Dict[str, Any] = {
        "license": ac.access_matrix(),
        "royalty_report": RoyaltyReporter.load(),
        "env_tier": raw,
        "env_tier_valid": env_tier_is_valid(raw),
    }
    warning = env_tier_warning()
    if warning:
        status["warning"] = warning
    return status


def enforce_batch_size(n: int, tier: Optional[str] = None) -> None:
    """Require ``batch`` and raise if *n* exceeds the tier's batch cap."""
    ac = AccessController(tier=tier)
    ac.require("batch")
    limit = max_batch_size(ac.tier)
    if limit is not None and n > limit:
        raise AccessController.AccessDeniedError(
            f"Feature 'unlimited_batch' is not available on the '{ac.tier}' tier. "
            f"Batch size {n} exceeds the {ac.tier} limit of {limit}. "
            f"Requires 'enterprise' or higher."
        )


def record_usage(
    *,
    setups: Optional[Iterable[str]] = None,
    signals: Optional[Iterable[Any]] = None,
    tickers: Optional[Iterable[str]] = None,
    report_path: Optional[Path] = None,
) -> Optional[Path]:
    """Record usage events and persist them. Never raises (offline-safe)."""
    try:
        setup_list = [str(s) for s in (setups or []) if s]
        signal_list = list(signals or [])
        ticker_list = [str(t) for t in (tickers or []) if t]
        if not setup_list and not signal_list and not ticker_list:
            return None
        rr = RoyaltyReporter(report_path=report_path)
        for symbol in setup_list:
            rr.record_setup(symbol)
        for sig in signal_list:
            if isinstance(sig, dict):
                rr.record_signal(str(sig.get("symbol", "")), str(sig.get("direction", "")))
            elif isinstance(sig, (tuple, list)) and sig:
                direction = str(sig[1]) if len(sig) > 1 else ""
                rr.record_signal(str(sig[0]), direction)
            elif sig:
                rr.record_signal(str(sig))
        if ticker_list:
            rr.record_tickers(ticker_list)
        return rr.save(merge=True)
    except Exception:
        return None
