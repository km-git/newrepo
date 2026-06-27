"""Track exported setup outcomes and feed hit rates back into gates and sizing."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_TF_ORDER = ("1w", "1d", "4h", "1h", "15m")

TRACKED_PATH = Path("output/autodream/tracked_setups.json")
METRICS_PATH = Path("output/autodream/metrics.json")
PERFORMANCE_MD = Path("reports/HISTORICAL_PERFORMANCE.md")

# Max forward bars to resolve a setup before marking expired.
_MAX_FORWARD_BARS = {"15m": 96, "1h": 72, "4h": 42, "1d": 30, "1w": 12}

_MIN_SAMPLES = 3
_POOR_WIN_RATE = 0.40
_STRONG_WIN_RATE = 0.55


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def _is_long(direction: str) -> bool:
  return str(direction).upper() in ("LONG", "BULL")


def _load_state() -> dict:
  if not TRACKED_PATH.exists():
    return {"open": [], "closed": []}
  try:
    return json.loads(TRACKED_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {"open": [], "closed": []}


def _save_state(state: dict) -> None:
  TRACKED_PATH.parent.mkdir(parents=True, exist_ok=True)
  state["updated"] = _utcnow()
  TRACKED_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def setup_key(symbol: str, timeframe: str, direction: str) -> str:
  return f"{symbol}|{timeframe}|{direction.upper()}"


def simulate_forward(
  direction: str,
  entry: float,
  stop: float,
  tp1: float,
  highs: List[float],
  lows: List[float],
) -> str:
  """Walk bars after entry: tp1 before stop wins; else sl_hit; else open."""
  if entry <= 0 or stop <= 0 or tp1 <= 0:
    return "invalid"
  long = _is_long(direction)
  for h, l in zip(highs, lows):
    if long:
      if l <= stop:
        return "sl_hit"
      if h >= tp1:
        return "tp1_hit"
    else:
      if h >= stop:
        return "sl_hit"
      if l <= tp1:
        return "tp1_hit"
  return "open"


def _row_to_tracked(row: dict, recorded_at: str) -> Optional[dict]:
  if row.get("row_type", "primary") != "primary":
    return None
  if row.get("gtc_tier") not in ("executable", "monitor"):
    return None
  try:
    wae = float(row.get("wae") or 0)
    stop = float(row.get("stop_loss") or 0)
    tp1 = float(row.get("tp1") or 0)
  except (TypeError, ValueError):
    return None
  if wae <= 0 or stop <= 0 or tp1 <= 0:
    return None
  sym = row.get("symbol", "")
  tf = row.get("timeframe", "")
  direction = row.get("direction", "")
  if not sym or not tf or not direction:
    return None
  return {
    "id": setup_key(sym, tf, direction),
    "recorded_at": recorded_at,
    "symbol": sym,
    "timeframe": tf,
    "direction": direction,
    "gtc_tier": row.get("gtc_tier"),
    "honest_execution_tier": row.get("honest_execution_tier"),
    "wae": wae,
    "stop_loss": stop,
    "tp1": tp1,
    "tp2": float(row.get("tp2") or 0) or None,
    "wave_structure": row.get("wave_structure"),
    "consensus": row.get("consensus"),
    "status": "open",
    "resolved_at": None,
    "bars_checked": 0,
  }


def record_setups(rows: List[dict], *, recorded_at: Optional[str] = None) -> int:
  """Append new open setups from export rows (dedupe by id while still open)."""
  recorded_at = recorded_at or _utcnow()
  state = _load_state()
  open_ids = {s["id"] for s in state["open"]}
  added = 0
  for row in rows:
    tracked = _row_to_tracked(row, recorded_at)
    if not tracked or tracked["id"] in open_ids:
      continue
    state["open"].append(tracked)
    open_ids.add(tracked["id"])
    added += 1
  if added:
    _save_state(state)
  return added


def _bars_after_record(df, recorded_at: str) -> Tuple[List[float], List[float], List[float]]:
  """OHLC rows strictly after the recorded timestamp."""
  if df is None or len(df) == 0:
    return [], [], []
  try:
    ts = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    if df.index.tz is None:
      mask = df.index >= ts.replace(tzinfo=None)
    else:
      mask = df.index >= ts
    sub = df.loc[mask]
    if len(sub) == 0:
      sub = df.tail(5)
    return (
      sub["High"].astype(float).tolist(),
      sub["Low"].astype(float).tolist(),
      sub["Close"].astype(float).tolist(),
    )
  except (ValueError, TypeError, KeyError):
    tail = df.tail(10)
    return (
      tail["High"].astype(float).tolist(),
      tail["Low"].astype(float).tolist(),
      tail["Close"].astype(float).tolist(),
    )


def resolve_open_setups(*, is_crypto: bool = True) -> int:
  """Mark open setups tp1_hit / sl_hit / expired using live OHLC."""
  from fetchers import fetch

  state = _load_state()
  if not state["open"]:
    return 0

  resolved = 0
  still_open: List[dict] = []
  fetch_cache: Dict[str, Any] = {}

  for setup in state["open"]:
    sym = setup["symbol"]
    tf = setup["timeframe"]
    max_bars = _MAX_FORWARD_BARS.get(tf, 48)
    cache_key = f"{sym}|{tf}"
    if cache_key not in fetch_cache:
      try:
        fetch_cache[cache_key] = fetch(sym, [tf], is_crypto=is_crypto).get(tf)
      except Exception:
        fetch_cache[cache_key] = None

    df = fetch_cache[cache_key]
    highs, lows, _closes = _bars_after_record(df, setup["recorded_at"])
    highs = highs[:max_bars]
    lows = lows[:max_bars]
    setup["bars_checked"] = len(highs)

    if not highs:
      still_open.append(setup)
      continue

    outcome = simulate_forward(
      setup["direction"],
      float(setup["wae"]),
      float(setup["stop_loss"]),
      float(setup["tp1"]),
      highs,
      lows,
    )
    if outcome == "open" and len(highs) >= max_bars:
      outcome = "expired"
    if outcome == "open":
      still_open.append(setup)
      continue

    setup["status"] = outcome
    setup["resolved_at"] = _utcnow()
    state["closed"].append(setup)
    resolved += 1

  state["open"] = still_open
  state["closed"] = state["closed"][-3000:]
  _save_state(state)
  return resolved


def compute_metrics(state: Optional[dict] = None) -> dict:
  """Aggregate win rates from closed tracked setups."""
  state = state or _load_state()
  closed = [s for s in state.get("closed", []) if s.get("status") in ("tp1_hit", "sl_hit", "expired")]

  def _bucket(key: str, items: List[dict]) -> dict:
    wins = sum(1 for s in items if s.get("status") == "tp1_hit")
    losses = sum(1 for s in items if s.get("status") == "sl_hit")
    expired = sum(1 for s in items if s.get("status") == "expired")
    decided = wins + losses
    return {
      "n": len(items),
      "wins": wins,
      "losses": losses,
      "expired": expired,
      "decided": decided,
      "win_rate": round(wins / decided, 3) if decided else None,
    }

  by_pair_tf: Dict[str, dict] = {}
  by_tf: Dict[str, List[dict]] = defaultdict(list)
  by_tier: Dict[str, List[dict]] = defaultdict(list)
  by_direction: Dict[str, List[dict]] = defaultdict(list)

  pair_tf_groups: Dict[str, List[dict]] = defaultdict(list)
  for s in closed:
    k = setup_key(s["symbol"], s["timeframe"], s["direction"])
    pair_tf_groups[k].append(s)
    by_tf[s["timeframe"]].append(s)
    tier = f"{s.get('gtc_tier')}|{s.get('honest_execution_tier')}"
    by_tier[tier].append(s)
    by_direction[s.get("direction", "?")].append(s)

  for k, items in pair_tf_groups.items():
    by_pair_tf[k] = _bucket(k, items)

  overall_wins = sum(1 for s in closed if s.get("status") == "tp1_hit")
  overall_losses = sum(1 for s in closed if s.get("status") == "sl_hit")
  overall_decided = overall_wins + overall_losses

  return {
    "updated": _utcnow(),
    "open_count": len(state.get("open", [])),
    "closed_count": len(closed),
    "overall": {
      "wins": overall_wins,
      "losses": overall_losses,
      "decided": overall_decided,
      "win_rate": round(overall_wins / overall_decided, 3) if overall_decided else None,
    },
    "by_pair_tf": by_pair_tf,
    "by_timeframe": {k: _bucket(k, v) for k, v in by_tf.items()},
    "by_tier": {k: _bucket(k, v) for k, v in by_tier.items()},
    "by_direction": {k: _bucket(k, v) for k, v in by_direction.items()},
  }


def save_metrics(metrics: dict) -> None:
  METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
  METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def load_metrics() -> dict:
  if not METRICS_PATH.exists():
    return compute_metrics()
  try:
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return compute_metrics()


def lookup_win_rate(metrics: dict, symbol: str, timeframe: str, direction: str) -> Tuple[Optional[float], int]:
  key = setup_key(symbol, timeframe, direction)
  bucket = metrics.get("by_pair_tf", {}).get(key)
  if bucket and bucket.get("decided", 0) >= _MIN_SAMPLES:
    return bucket.get("win_rate"), bucket["decided"]
  tf_bucket = metrics.get("by_timeframe", {}).get(timeframe)
  if tf_bucket and tf_bucket.get("decided", 0) >= _MIN_SAMPLES:
    return tf_bucket.get("win_rate"), tf_bucket["decided"]
  overall = metrics.get("overall", {})
  if overall.get("decided", 0) >= _MIN_SAMPLES:
    return overall.get("win_rate"), overall["decided"]
  return None, bucket.get("decided", 0) if bucket else 0


def feedback_for_row(row: dict, metrics: dict) -> dict:
  """Historical feedback for a limit-order row."""
  sym = row.get("symbol", "")
  tf = row.get("timeframe", "")
  direction = row.get("direction", "")
  win_rate, n = lookup_win_rate(metrics, sym, tf, direction)

  out: Dict[str, Any] = {
    "hist_win_rate": win_rate,
    "hist_n": n,
    "hist_action": "none",
    "tier_override": None,
    "size_cap_mult": 1.0,
    "readiness_delta": 0,
  }
  if win_rate is None or n < _MIN_SAMPLES:
    out["hist_note"] = f"insufficient history (n={n})"
    return out

  if win_rate < _POOR_WIN_RATE:
    out["hist_action"] = "downgrade"
    out["size_cap_mult"] = 0.75
    out["readiness_delta"] = -8
    if row.get("gtc_tier") == "executable" and row.get("honest_execution_tier") == "probe":
      out["tier_override"] = "monitor"
    out["hist_note"] = f"poor track record {win_rate:.0%} over {n} — size −25%"
  elif win_rate > _STRONG_WIN_RATE:
    out["hist_action"] = "boost"
    out["size_cap_mult"] = 1.10
    out["readiness_delta"] = 5
    out["hist_note"] = f"strong track record {win_rate:.0%} over {n} — size +10%"
  else:
    out["hist_action"] = "neutral"
    out["hist_note"] = f"neutral history {win_rate:.0%} over {n}"

  return out


def apply_feedback_to_row(row: dict, metrics: dict) -> dict:
  """Apply historical feedback to a limit-order row (tier + size cap)."""
  fb = feedback_for_row(row, metrics)
  row = dict(row)
  row["hist_win_rate"] = fb.get("hist_win_rate")
  row["hist_n"] = fb.get("hist_n")
  row["hist_action"] = fb.get("hist_action")
  row["hist_note"] = fb.get("hist_note")

  if fb.get("tier_override"):
    row["gtc_tier"] = fb["tier_override"]
    row["tier_note"] = f"{row.get('tier_note', '')} | HIST downgrade: {fb['hist_note']}".strip(" |")

  mult = float(fb.get("size_cap_mult") or 1.0)
  if mult != 1.0 and row.get("gtc_size_cap_pct"):
    row["gtc_size_cap_pct"] = round(min(100, max(10, float(row["gtc_size_cap_pct"]) * mult)), 1)

  return row


def apply_feedback_to_rows(rows: List[dict], metrics: Optional[dict] = None) -> List[dict]:
  metrics = metrics or load_metrics()
  return [apply_feedback_to_row(r, metrics) for r in rows]


def readiness_adjustment(symbol: str, timeframe: str, direction: str, metrics: Optional[dict] = None) -> int:
  """Readiness score delta from tracked outcomes (−8..+5)."""
  metrics = metrics or load_metrics()
  fb = feedback_for_row(
    {"symbol": symbol, "timeframe": timeframe, "direction": direction, "gtc_tier": "monitor"},
    metrics,
  )
  return int(fb.get("readiness_delta") or 0)


def run_learning_phase(*, is_crypto: bool = True, record_rows: Optional[List[dict]] = None) -> dict:
  """
  Full loop: resolve open → compute metrics → save → optional record new setups.
  Returns metrics dict for export pipeline.
  """
  resolved = resolve_open_setups(is_crypto=is_crypto)
  metrics = compute_metrics()
  metrics["last_resolved"] = resolved
  save_metrics(metrics)
  save_performance_report(metrics)

  if record_rows:
    metrics["newly_recorded"] = record_setups(record_rows)

  return metrics


def save_performance_report(metrics: dict) -> None:
  """Write human-readable historical performance to reports/."""
  PERFORMANCE_MD.parent.mkdir(parents=True, exist_ok=True)
  lines = [
    "# Historical Setup Performance",
    "",
    f"Updated: **{metrics.get('updated', _utcnow())}**",
    "",
    "## Overall",
    "",
    f"| Wins | Losses | Decided | Win rate | Open |",
    f"|------|--------|---------|----------|------|",
  ]
  o = metrics.get("overall", {})
  wr = o.get("win_rate")
  wr_s = f"{wr:.1%}" if wr is not None else "—"
  lines.append(
    f"| {o.get('wins', 0)} | {o.get('losses', 0)} | {o.get('decided', 0)} | {wr_s} | {metrics.get('open_count', 0)} |"
  )

  lines.extend(["", "## By timeframe", "", "| TF | Wins | Losses | Win rate | n |", "|----|------|--------|----------|---|"])
  for tf in _TF_ORDER:
    b = metrics.get("by_timeframe", {}).get(tf, {})
    wr = b.get("win_rate")
    wr_s = f"{wr:.1%}" if wr is not None else "—"
    lines.append(f"| {tf} | {b.get('wins', 0)} | {b.get('losses', 0)} | {wr_s} | {b.get('n', 0)} |")

  pair_tf = metrics.get("by_pair_tf", {})
  if pair_tf:
    lines.extend(["", "## By pair × TF (decided ≥ 1)", "", "| Key | Wins | Losses | Win rate | n |", "|-----|------|--------|----------|---|"])
    for k, b in sorted(pair_tf.items(), key=lambda x: (-(x[1].get("decided") or 0), x[0]))[:40]:
      wr = b.get("win_rate")
      wr_s = f"{wr:.1%}" if wr is not None else "—"
      lines.append(f"| {k} | {b.get('wins', 0)} | {b.get('losses', 0)} | {wr_s} | {b.get('n', 0)} |")

  lines.extend([
    "",
    "> Source: `output/autodream/tracked_setups.json` · Metrics: `output/autodream/metrics.json`",
    "",
    "Feedback rules: win rate < 40% → −25% size, probe executable → monitor; > 55% → +10% size, +5 readiness.",
  ])
  PERFORMANCE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def seed_from_export_csv(csv_path: Path, recorded_at: Optional[str] = None) -> int:
  """Bootstrap tracker from an existing limit orders CSV (one-time / tests)."""
  import csv

  if not csv_path.exists():
    return 0
  rows = list(csv.DictReader(csv_path.open()))
  return record_setups(rows, recorded_at=recorded_at or _utcnow())
