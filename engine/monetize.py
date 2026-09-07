"""Signal licensing + royalty desk (Monetization Strategy Services).

Adapts the tape-to-cloud "monetize" module concept (license tagging,
access control, royalty reporting) to Elliott Wave + harmonic trade
setups.

The module is deterministic and side-effect-free apart from the report
writers at the bottom. No LLM calls, no network. It consumes the same
setup dicts produced by :mod:`engine.limit_orders_export` /
:mod:`engine.best_trades` / :mod:`scripts.export_go_setups`, and the same
resolved-outcome dicts persisted by :mod:`engine.outcome_tracker` under
``output/autodream/tracked_setups.json`` (``closed`` list, ``status`` in
``tp1_hit`` / ``sl_hit`` / ``expired``).

Watermarks are SHA-256 hashes over the canonical JSON of the source
signal — the same chain-of-custody principle in Section 5 of the
tape-to-cloud blueprint, adapted to trading signals.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

TIER_FREE = "free"
TIER_PRO = "pro"
TIER_ENTERPRISE = "enterprise"

ALL_TIERS = (TIER_FREE, TIER_PRO, TIER_ENTERPRISE)

# Where the CLI writes reports; overridable by env for tests.
REPORT_JSON = Path(os.environ.get("EW_MONETIZE_JSON", "output/monetize/latest_report.json"))
REPORT_MD = Path(os.environ.get("EW_MONETIZE_MD", "reports/MONETIZATION_STRATEGY.md"))

# Public fields per tier — anything not in this set is redacted / removed.
# Free tier deliberately hides exact entry / SL / TP so the tier still has
# to buy Pro to trade the signal; only side + timeframe + delayed context.
_FREE_PUBLIC_FIELDS: frozenset = frozenset({
  "symbol",
  "timeframe",
  "direction",
  "gtc_tier",
  "honest_execution_tier",
  "delayed_hint",
})
_PRO_HIDDEN_FIELDS: frozenset = frozenset({
  # Everything else is exposed at Pro; only enterprise-only detail is hidden.
  "custom_risk_profile",
  "paper_fill_trace",
  "royalty_receiver",
})


@dataclass(frozen=True)
class TierPolicy:
  """Tier access + fee matrix.

  ``tf_allowlist`` and ``symbol_allowlist`` are treated as ``None`` == allow all.
  ``redistribution`` is advisory (embedded in the license block) — the runtime
  filter never enforces sharing itself, only labels intent.
  ``delay_hours`` controls "how stale is the copy the tier gets"; the filter
  emits it in the license so downstream consumers can honour or reject.
  """

  tier: str
  monthly_price_aud: float
  royalty_pct_of_r: float
  tf_allowlist: Optional[frozenset] = None
  symbol_allowlist: Optional[frozenset] = None
  redistribution_allowed: bool = False
  delay_hours: float = 0.0
  max_signals_per_day: Optional[int] = None
  paper_fill_included: bool = False
  custom_risk_profile: bool = False

  def allows_tf(self, tf: str) -> bool:
    if self.tf_allowlist is None:
      return True
    return str(tf) in self.tf_allowlist

  def allows_symbol(self, symbol: str) -> bool:
    if self.symbol_allowlist is None:
      return True
    return str(symbol) in self.symbol_allowlist


def default_tier_policies() -> Dict[str, TierPolicy]:
  """Reference three-tier ladder used by :func:`get_policy` and the CLI.

  Numbers are AUD and mirror the "50-55 bets, A$0-500/mo run cost" portfolio
  posture in ``discovery-output.md`` — this is a bet, not a priced product.
  """
  return {
    TIER_FREE: TierPolicy(
      tier=TIER_FREE,
      monthly_price_aud=0.0,
      royalty_pct_of_r=0.0,
      tf_allowlist=frozenset({"1d", "1w"}),
      redistribution_allowed=True,
      delay_hours=24.0,
      max_signals_per_day=3,
    ),
    TIER_PRO: TierPolicy(
      tier=TIER_PRO,
      monthly_price_aud=49.0,
      royalty_pct_of_r=0.0,
      tf_allowlist=None,
      redistribution_allowed=False,
      delay_hours=0.0,
    ),
    TIER_ENTERPRISE: TierPolicy(
      tier=TIER_ENTERPRISE,
      monthly_price_aud=249.0,
      royalty_pct_of_r=0.10,
      tf_allowlist=None,
      redistribution_allowed=False,
      delay_hours=0.0,
      paper_fill_included=True,
      custom_risk_profile=True,
    ),
  }


def get_policy(tier: str, policies: Optional[Dict[str, TierPolicy]] = None) -> TierPolicy:
  policies = policies or default_tier_policies()
  key = str(tier or "").lower().strip()
  if key not in policies:
    raise ValueError(f"unknown tier: {tier!r} (known: {sorted(policies)})")
  return policies[key]


def _signal_identity(signal: dict) -> Dict[str, Any]:
  """Stable, minimal identity for hashing / watermark id.

  Only the fields that make a signal materially distinct are used; volatile
  metadata (timestamps not present in the source signal, license blocks
  themselves) is excluded so hashes are deterministic and tamper-evident.
  """
  return {
    "symbol": signal.get("symbol"),
    "timeframe": signal.get("timeframe"),
    "direction": signal.get("direction"),
    "wae": signal.get("wae"),
    "stop_loss": signal.get("stop_loss"),
    "tp1": signal.get("tp1"),
    "tp2": signal.get("tp2"),
    "tp3": signal.get("tp3"),
    "gtc_tier": signal.get("gtc_tier"),
    "honest_execution_tier": signal.get("honest_execution_tier"),
  }


def _canonical_bytes(obj: Any) -> bytes:
  return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def signal_hash(signal: dict) -> str:
  """Deterministic SHA-256 over the signal's identity subset."""
  return hashlib.sha256(_canonical_bytes(_signal_identity(signal))).hexdigest()


def watermark_id(signal: dict, tier: str) -> str:
  """Tier-scoped watermark id: `wm_<tier>_<12-hex>` from signal hash."""
  h = hashlib.sha256(
    _canonical_bytes({"h": signal_hash(signal), "tier": tier})
  ).hexdigest()
  return f"wm_{tier}_{h[:12]}"


def _redact_free(signal: dict) -> Dict[str, Any]:
  """Free tier: side + tf + delayed hint only; hide entry / SL / TP."""
  wae = signal.get("wae")
  hint = None
  try:
    if wae not in (None, ""):
      hint = f"~{float(wae):.4g}"
  except (TypeError, ValueError):
    hint = None
  redacted = {k: signal.get(k) for k in _FREE_PUBLIC_FIELDS if k != "delayed_hint"}
  if hint is not None:
    redacted["delayed_hint"] = hint
  return redacted


def _redact_pro(signal: dict) -> Dict[str, Any]:
  """Pro tier: full signal minus enterprise-only fields."""
  return {k: v for k, v in signal.items() if k not in _PRO_HIDDEN_FIELDS}


def _redact_enterprise(signal: dict) -> Dict[str, Any]:
  return dict(signal)


_REDACTORS = {
  TIER_FREE: _redact_free,
  TIER_PRO: _redact_pro,
  TIER_ENTERPRISE: _redact_enterprise,
}


@dataclass
class SignalLicense:
  """License block attached to a licensed signal.

  ``signal_hash`` is the SHA-256 of the original signal identity so the
  license is tamper-evident: any change to symbol/tf/direction/entry/SL/TP
  invalidates the hash. ``watermark_id`` is a tier-scoped id derived from
  the same hash; the royalty report uses it to reconcile ownership.
  """

  signal_id: str
  tier: str
  redistribution_allowed: bool
  tf_allowlist: Optional[List[str]]
  symbol_allowlist: Optional[List[str]]
  expiry_utc: Optional[str]
  watermark_id: str
  signal_hash: str
  issued_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

  def to_dict(self) -> Dict[str, Any]:
    return asdict(self)


def _royalty_terms(policy: TierPolicy) -> Dict[str, Any]:
  return {
    "tier": policy.tier,
    "monthly_price_aud": policy.monthly_price_aud,
    "royalty_pct_of_r": policy.royalty_pct_of_r,
    "paper_fill_included": policy.paper_fill_included,
    "custom_risk_profile": policy.custom_risk_profile,
    "delay_hours": policy.delay_hours,
    "redistribution_allowed": policy.redistribution_allowed,
  }


def _signal_id(signal: dict) -> str:
  sid = signal.get("id")
  if sid:
    return str(sid)
  return "|".join(str(signal.get(k) or "") for k in ("symbol", "timeframe", "direction"))


def _expiry_for(policy: TierPolicy, signal: dict) -> Optional[str]:
  """Tier expiry — free tier expires with the delay window, others open-ended."""
  if policy.tier == TIER_FREE and policy.delay_hours > 0:
    return f"delayed_{int(policy.delay_hours)}h"
  return None


def apply_license(
  signals: Sequence[dict],
  tier: str,
  *,
  policies: Optional[Dict[str, TierPolicy]] = None,
) -> List[Dict[str, Any]]:
  """Filter + redact + license a list of signals for a tier.

  Skips signals whose ``timeframe`` or ``symbol`` is not in the tier's
  allowlist; caps by ``max_signals_per_day`` when set. Each surviving
  signal is redacted according to the tier and gets a ``license`` and
  ``royalty_terms`` block attached.
  """
  policy = get_policy(tier, policies)
  redactor = _REDACTORS[policy.tier]
  out: List[Dict[str, Any]] = []
  seen = 0
  for signal in signals:
    if not isinstance(signal, dict):
      continue
    tf = str(signal.get("timeframe") or "")
    sym = str(signal.get("symbol") or "")
    if not policy.allows_tf(tf):
      continue
    if not policy.allows_symbol(sym):
      continue
    if policy.max_signals_per_day is not None and seen >= policy.max_signals_per_day:
      break
    body = redactor(signal)
    lic = SignalLicense(
      signal_id=_signal_id(signal),
      tier=policy.tier,
      redistribution_allowed=policy.redistribution_allowed,
      tf_allowlist=sorted(policy.tf_allowlist) if policy.tf_allowlist else None,
      symbol_allowlist=sorted(policy.symbol_allowlist) if policy.symbol_allowlist else None,
      expiry_utc=_expiry_for(policy, signal),
      watermark_id=watermark_id(signal, policy.tier),
      signal_hash=signal_hash(signal),
    )
    body["license"] = lic.to_dict()
    body["royalty_terms"] = _royalty_terms(policy)
    out.append(body)
    seen += 1
  return out


def _r_from_outcome(outcome: dict) -> Optional[float]:
  """R-multiple realized on an outcome dict from :mod:`engine.outcome_tracker`.

  For ``sl_hit`` the loss is -1R. For ``tp1_hit`` the win is (tp1-entry)/risk
  scaled by ``tp1_exit_pct`` (fraction of position taken at TP1) so a partial
  fill returns a partial R. ``expired`` returns 0R.
  """
  status = outcome.get("status")
  if status == "sl_hit":
    return -1.0
  if status == "expired":
    return 0.0
  if status != "tp1_hit":
    return None
  try:
    entry = float(outcome.get("wae") or 0)
    stop = float(outcome.get("stop_loss") or 0)
    tp1 = float(outcome.get("tp1") or 0)
  except (TypeError, ValueError):
    return None
  risk = abs(entry - stop)
  if risk <= 0 or entry <= 0 or tp1 <= 0:
    return None
  reward = abs(tp1 - entry)
  partial = float(outcome.get("tp1_exit_pct") or 100) / 100.0
  return round((reward / risk) * partial, 4)


def _tier_of(outcome: dict, default: str = TIER_PRO) -> Optional[str]:
  """Which tier "owned" the licensed signal.

  When ``license_tier`` / ``tier`` is absent (or empty) fall back to
  ``default``. When it *is* present but unknown, return ``None`` so the
  caller can flag the outcome as invalid rather than silently absorb it.
  """
  raw = outcome.get("license_tier") or outcome.get("tier")
  if raw in (None, ""):
    return default
  tier = str(raw).lower().strip()
  if tier in ALL_TIERS:
    return tier
  return None


def royalty_report(
  resolved_outcomes: Sequence[dict],
  tier_policy: Optional[Dict[str, TierPolicy]] = None,
  *,
  active_subscribers: Optional[Dict[str, int]] = None,
  months: int = 1,
) -> Dict[str, Any]:
  """Audit-ready royalty + revenue report.

  Parameters
  ----------
  resolved_outcomes
    ``closed`` list entries from ``output/autodream/tracked_setups.json``
    (or any dict with ``status`` / ``wae`` / ``stop_loss`` / ``tp1`` /
    ``tp1_exit_pct``). May carry a ``license_tier`` (or ``tier``) key to
    attribute outcomes to a tier; otherwise defaults to Pro.
  tier_policy
    Optional custom policy map; defaults to :func:`default_tier_policies`.
  active_subscribers
    Optional ``{tier: count}`` — drives subscription revenue.
  months
    Billing period length used to multiply monthly price × subscribers.

  Returns a JSON-serialisable dict with per-tier revenue, W/L counts,
  R-based royalty owed, and watermark reconciliation counts.
  """
  policies = tier_policy or default_tier_policies()
  subs = active_subscribers or {}

  per_tier: Dict[str, Dict[str, Any]] = {}
  for tier, policy in policies.items():
    n = int(subs.get(tier, 0) or 0)
    per_tier[tier] = {
      "tier": tier,
      "subscribers": n,
      "monthly_price_aud": policy.monthly_price_aud,
      "royalty_pct_of_r": policy.royalty_pct_of_r,
      "subscription_revenue_aud": round(policy.monthly_price_aud * n * months, 2),
      "wins": 0,
      "losses": 0,
      "expired": 0,
      "n_resolved": 0,
      "sum_r": 0.0,
      "positive_r": 0.0,
      "royalty_r": 0.0,
      "watermarks": set(),
    }

  invalid = 0
  for outcome in resolved_outcomes:
    if not isinstance(outcome, dict):
      invalid += 1
      continue
    tier = _tier_of(outcome)
    if tier is None or tier not in per_tier:
      invalid += 1
      continue
    bucket = per_tier[tier]
    bucket["n_resolved"] += 1
    status = outcome.get("status")
    if status == "tp1_hit":
      bucket["wins"] += 1
    elif status == "sl_hit":
      bucket["losses"] += 1
    elif status == "expired":
      bucket["expired"] += 1
    r = _r_from_outcome(outcome)
    if r is None:
      invalid += 1
      continue
    bucket["sum_r"] = round(bucket["sum_r"] + r, 4)
    if r > 0:
      bucket["positive_r"] = round(bucket["positive_r"] + r, 4)
    wm = outcome.get("watermark_id")
    if wm:
      bucket["watermarks"].add(str(wm))

  totals = {
    "subscribers": 0,
    "subscription_revenue_aud": 0.0,
    "royalty_revenue_aud": 0.0,
    "total_revenue_aud": 0.0,
    "n_resolved": 0,
    "sum_r": 0.0,
    "positive_r": 0.0,
  }
  for tier, bucket in per_tier.items():
    policy = policies[tier]
    royalty_r = round(bucket["positive_r"] * policy.royalty_pct_of_r, 4)
    bucket["royalty_r"] = royalty_r
    bucket["royalty_owed_r"] = royalty_r
    bucket["decided"] = bucket["wins"] + bucket["losses"]
    if bucket["decided"]:
      bucket["win_rate"] = round(bucket["wins"] / bucket["decided"], 3)
    else:
      bucket["win_rate"] = None
    bucket["watermark_count"] = len(bucket["watermarks"])
    bucket["watermarks"] = sorted(bucket["watermarks"])

    totals["subscribers"] += bucket["subscribers"]
    totals["subscription_revenue_aud"] = round(
      totals["subscription_revenue_aud"] + bucket["subscription_revenue_aud"], 2
    )
    totals["royalty_revenue_aud"] = round(
      totals["royalty_revenue_aud"] + royalty_r, 4
    )
    totals["total_revenue_aud"] = round(
      totals["subscription_revenue_aud"] + totals["royalty_revenue_aud"], 4
    )
    totals["n_resolved"] += bucket["n_resolved"]
    totals["sum_r"] = round(totals["sum_r"] + bucket["sum_r"], 4)
    totals["positive_r"] = round(totals["positive_r"] + bucket["positive_r"], 4)

  return {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "months": months,
    "per_tier": per_tier,
    "totals": totals,
    "invalid_outcomes": invalid,
    "note": (
      "Royalty is a percentage of realized positive R multiples on resolved "
      "outcomes. Losses do not clawback subscription revenue. Watermark counts "
      "are unique per tier — reconcile against issued licenses for tamper checks."
    ),
  }


def _load_json(path: Path) -> Any:
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _load_signals_from_disk() -> List[dict]:
  """Best-effort load: prefer best_trades_latest.json (v6 scanner output),
  fall back to raw limit-order CSV rows. Returns [] when neither exists."""
  candidates = [
    Path("output/v6_scanner/best_trades_latest.json"),
  ]
  for p in candidates:
    if not p.exists():
      continue
    data = _load_json(p)
    if isinstance(data, dict) and data.get("top_10"):
      return list(data["top_10"])
    if isinstance(data, list):
      return [row for row in data if isinstance(row, dict)]

  csv_path = Path("output/v6_scanner/best_trades_latest.csv")
  if csv_path.exists():
    import csv as _csv

    with csv_path.open(encoding="utf-8") as f:
      return list(_csv.DictReader(f))
  return []


def _load_outcomes_from_disk() -> List[dict]:
  tracked = Path("output/autodream/tracked_setups.json")
  data = _load_json(tracked) or {}
  closed = data.get("closed") or []
  return [c for c in closed if isinstance(c, dict)]


def _fallback_subscribers() -> Dict[str, int]:
  """Illustrative subscriber counts (bet-mode placeholder)."""
  return {TIER_FREE: 25, TIER_PRO: 5, TIER_ENTERPRISE: 1}


def build_report(
  *,
  tier: Optional[str] = None,
  signals: Optional[Sequence[dict]] = None,
  outcomes: Optional[Sequence[dict]] = None,
  subscribers: Optional[Dict[str, int]] = None,
  months: int = 1,
) -> Dict[str, Any]:
  """Combined license + royalty snapshot used by the CLI."""
  policies = default_tier_policies()
  raw_signals = list(signals) if signals is not None else _load_signals_from_disk()
  raw_outcomes = list(outcomes) if outcomes is not None else _load_outcomes_from_disk()
  subs = subscribers if subscribers is not None else _fallback_subscribers()

  tiers = [tier.lower()] if tier else list(ALL_TIERS)
  licensed = {t: apply_license(raw_signals, t, policies=policies) for t in tiers}
  royalty = royalty_report(raw_outcomes, policies, active_subscribers=subs, months=months)

  return {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "tier_scope": tiers,
    "input": {
      "signal_count": len(raw_signals),
      "outcome_count": len(raw_outcomes),
      "subscribers": subs,
    },
    "licensed_signals": {t: licensed[t] for t in tiers},
    "royalty_report": royalty,
  }


def _fmt_aud(value: float) -> str:
  try:
    return f"A${float(value):,.2f}"
  except (TypeError, ValueError):
    return "—"


def _render_report_md(report: Dict[str, Any]) -> str:
  royalty = report.get("royalty_report") or {}
  per_tier = royalty.get("per_tier") or {}
  totals = royalty.get("totals") or {}
  lines: List[str] = [
    "# Monetization Strategy — Signal Licensing & Royalty Desk",
    "",
    f"Generated: **{report.get('generated_at_utc', '—')}**",
    "",
    "> Bet-mode module. Turns EW + harmonic setups into a tiered signal service ",
    "> with license watermarking and R-based royalty accounting.",
    "",
    "## Inputs",
    "",
    f"- Signals loaded: **{report['input']['signal_count']}**",
    f"- Resolved outcomes: **{report['input']['outcome_count']}**",
    f"- Subscribers: `{report['input']['subscribers']}`",
    f"- Billing months: **{royalty.get('months', 1)}**",
    "",
    "## Per-tier revenue",
    "",
    "| Tier | Subs | Sub revenue | Wins | Losses | Decided WR | Σ R | +R | Royalty (R) |",
    "|------|------|-------------|------|--------|------------|-----|----|-------------|",
  ]
  for tier in ALL_TIERS:
    b = per_tier.get(tier) or {}
    wr = b.get("win_rate")
    wr_s = f"{wr:.1%}" if wr is not None else "—"
    lines.append(
      f"| {tier} | {b.get('subscribers', 0)} | {_fmt_aud(b.get('subscription_revenue_aud', 0))} | "
      f"{b.get('wins', 0)} | {b.get('losses', 0)} | {wr_s} | "
      f"{b.get('sum_r', 0):.2f} | {b.get('positive_r', 0):.2f} | {b.get('royalty_r', 0):.4f} |"
    )
  lines.extend([
    "",
    "## Totals",
    "",
    f"- Subscribers: **{totals.get('subscribers', 0)}**",
    f"- Subscription revenue: **{_fmt_aud(totals.get('subscription_revenue_aud', 0))}**",
    f"- Royalty revenue (R): **{totals.get('royalty_revenue_aud', 0):.4f}**",
    f"- Total revenue (subs + royalty proxy): **{_fmt_aud(totals.get('total_revenue_aud', 0))}**",
    "",
    "## Licensed signals (sample per tier)",
    "",
  ])
  for tier, rows in (report.get("licensed_signals") or {}).items():
    lines.append(f"### {tier} — {len(rows)} signals after policy filter")
    lines.append("")
    for row in rows[:5]:
      lic = row.get("license") or {}
      lines.append(
        f"- `{row.get('symbol', '?')} {row.get('timeframe', '?')} {row.get('direction', '?')}` "
        f"→ wm `{lic.get('watermark_id')}` hash `{lic.get('signal_hash', '')[:10]}…` "
        f"expiry `{lic.get('expiry_utc') or 'open'}`"
      )
    if not rows:
      lines.append("- (no signals passed the tier policy filter)")
    lines.append("")
  lines.extend([
    "## Notes",
    "",
    "- Watermarks are SHA-256 over the signal identity subset (symbol, tf, ",
    "  direction, WAE, SL, TPs, tiers). Any edit invalidates the hash.",
    "- Free tier redacts entry / SL / TP; Pro exposes full signal; Enterprise ",
    "  additionally exposes paper-fill trace and custom risk profile.",
    "- Royalty is percent-of-positive-R on resolved outcomes (see engine/monetize.py).",
    "- Source data: `output/v6_scanner/best_trades_latest.json`, ",
    "  `output/autodream/tracked_setups.json` (closed list).",
    "",
  ])
  return "\n".join(lines)


def write_reports(report: Dict[str, Any], *, json_path: Optional[Path] = None, md_path: Optional[Path] = None) -> Dict[str, str]:
  """Persist ``build_report`` output to JSON + Markdown. Returns final paths."""
  jp = json_path or REPORT_JSON
  mp = md_path or REPORT_MD
  jp.parent.mkdir(parents=True, exist_ok=True)
  mp.parent.mkdir(parents=True, exist_ok=True)
  jp.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
  mp.write_text(_render_report_md(report), encoding="utf-8")
  return {"json": str(jp), "md": str(mp)}


def run_monetize_report(
  *,
  tier: Optional[str] = None,
  months: int = 1,
) -> Dict[str, Any]:
  """CLI entry point used by ``ew_tool.py --monetize-report``."""
  report = build_report(tier=tier, months=months)
  paths = write_reports(report)
  return {
    "ok": True,
    "tier": tier,
    "signal_count": report["input"]["signal_count"],
    "outcome_count": report["input"]["outcome_count"],
    "totals": report["royalty_report"]["totals"],
    "paths": paths,
  }
