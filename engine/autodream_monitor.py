"""Autodream monitor — re-scan queue, evaluate triggers, upgrade/downgrade setups."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.atr import compute_atr14, median_daily_range
from core.impulse import validate_impulse
from core.monowaves import adaptive_skip_for_df, compute_skip, extract_monowaves_cached
from engine.outcomes import STYLE_CONFIG
from fetchers import fetch

DEFAULT_QUEUE_PATH = Path("output/autodream/monitor_queue.json")
EVENTS_PATH = Path("output/autodream/monitor_events.jsonl")

STYLE_CHECK_TF = {style: cfg["primary_tf"] for style, cfg in STYLE_CONFIG.items()}


def load_monitor_queue(path: str | Path = DEFAULT_QUEUE_PATH) -> dict:
  p = Path(path)
  if not p.exists():
    return {"updated": None, "queue": []}
  with p.open() as f:
    return json.load(f)


def _dir_to_impulse(direction: str) -> str:
  return "BULL" if direction == "LONG" else "BEAR"


def _opposite_impulse(direction: str) -> str:
  return "BEAR" if direction == "LONG" else "BULL"


def _zone_bounds(zone: Optional[List[float]], entry: Optional[float], atr: float) -> Tuple[float, float]:
  if zone and len(zone) >= 2:
    return min(zone[0], zone[1]), max(zone[0], zone[1])
  if entry is not None:
    pad = max(atr * 0.5, entry * 0.005)
    return entry - pad, entry + pad
  return 0.0, 0.0


def rejection_wick(df, direction: str) -> bool:
  """Last bar shows rejection in trade direction."""
  if df is None or len(df) < 1:
    return False
  row = df.iloc[-1]
  o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
  body = abs(c - o) or 1e-9
  lower_wick = min(o, c) - l
  upper_wick = h - max(o, c)
  if direction == "LONG":
    return lower_wick / body >= 1.2 and c >= o
  return upper_wick / body >= 1.2 and c <= o


def impulse_on_tf(mws: List[dict]) -> dict:
  """Best impulse read on a timeframe's monowaves."""
  if len(mws) < 5:
    return {"passes": False, "direction": "n/a", "violations": ["<5 monowaves"]}
  for start in range(len(mws) - 4):
    val = validate_impulse(mws[start : start + 5])
    if val["passes"]:
      return val
  return validate_impulse(mws[-5:])


def evaluate_triggers(
  item: dict,
  data: Dict[str, Any],
  adaptive: Dict[str, dict],
) -> dict:
  """
  Evaluate upgrade / invalidate triggers for one queue item.
  Returns scan result with triggers_hit, new_status, and reasons.
  """
  style = item["style"]
  direction = item.get("direction", "LONG")
  check_tf = item.get("check") or STYLE_CHECK_TF.get(style, "1d")
  impulse_dir = _dir_to_impulse(direction)

  df_check = data.get(check_tf)
  df_1d = data.get("1d")
  if df_check is None or len(df_check) < 5:
    return {
      "scanned_at": datetime.now(timezone.utc).isoformat(),
      "error": f"missing {check_tf} data",
      "triggers_hit": [],
      "invalidated": False,
      "new_status": item.get("status", "monitor"),
      "price": None,
    }

  price = float(df_check["Close"].iloc[-1])
  atr = compute_atr14(df_check)
  zone = item.get("entry_zone")
  z_low, z_high = _zone_bounds(zone, item.get("entry"), atr)
  in_zone = z_low <= price <= z_high

  mws = adaptive.get(check_tf, {}).get("monowaves", [])
  impulse = impulse_on_tf(mws)
  impulse_aligned = impulse.get("passes") and impulse.get("direction") == impulse_dir
  impulse_opposite = impulse.get("passes") and impulse.get("direction") == _opposite_impulse(direction)
  wick = rejection_wick(df_check, direction)

  close_1d = float(df_1d["Close"].iloc[-1]) if df_1d is not None and len(df_1d) else price
  stop = item.get("stop")
  stop_breached = False
  if stop is not None:
    if direction == "LONG":
      stop_breached = close_1d < stop
    else:
      stop_breached = close_1d > stop

  triggers_hit: List[str] = []
  if impulse_aligned:
    triggers_hit.append(f"{check_tf} impulse passes R1/R2/R3 ({impulse_dir})")
  if in_zone:
    triggers_hit.append("price in entry zone")
  if wick:
    triggers_hit.append("rejection wick on last bar")

  invalidated = stop_breached or impulse_opposite
  invalidate_reasons: List[str] = []
  if stop_breached:
    invalidate_reasons.append(f"1d close {close_1d:.4g} beyond stop {stop}")
  if impulse_opposite:
    invalidate_reasons.append(f"{check_tf} impulse flipped {_opposite_impulse(direction)}")

  prior = item.get("status", "monitor")
  if invalidated:
    new_status = "invalidated"
  elif prior == "executable":
    new_status = "executable" if impulse_aligned and not impulse_opposite else "monitor"
  elif impulse_aligned and (in_zone or wick):
    new_status = "executable"
  else:
    new_status = "monitor"

  upgrade_note = None
  if prior == "monitor" and new_status == "executable":
    upgrade_note = "UPGRADED monitor→executable: " + "; ".join(triggers_hit)
  elif prior == "executable" and new_status == "monitor":
    upgrade_note = "DOWNGRADED executable→monitor: impulse lost or invalidated pending"

  return {
    "scanned_at": datetime.now(timezone.utc).isoformat(),
    "symbol": item["symbol"],
    "style": style,
    "check_tf": check_tf,
    "price": round(price, 6),
    "entry_zone": [round(z_low, 6), round(z_high, 6)],
    "in_zone": in_zone,
    "impulse_valid": impulse_aligned,
    "impulse_opposite": impulse_opposite,
    "rejection_wick": wick,
    "triggers_hit": triggers_hit,
    "invalidated": invalidated,
    "invalidate_reasons": invalidate_reasons,
    "prior_status": prior,
    "new_status": new_status,
    "upgrade_note": upgrade_note,
  }


def _build_adaptive(symbol: str, data: dict, tfs: List[str]) -> dict:
  adaptive: Dict[str, dict] = {}
  for tf in tfs:
    if tf not in data:
      continue
    df = data[tf]
    atr = compute_atr14(df)
    med = median_daily_range(df)
    skip = compute_skip(atr, med)
    tag = f"monitor_{symbol}_{tf}"
    mws = extract_monowaves_cached(df, skip, cache_tag=tag)
    adaptive[tf] = {"skip": skip, "monowaves": mws, "atr_14": atr}
  return adaptive


def scan_queue_item(item: dict, is_crypto: bool = True, tfs: Optional[List[str]] = None) -> dict:
  """Fetch fresh data and evaluate one monitor queue item."""
  symbol = item["symbol"]
  style = item["style"]
  check_tf = item.get("check") or STYLE_CHECK_TF.get(style, "1d")
  need_tfs = list(dict.fromkeys(tfs or ["1d", "4h", "1h", "15m", "1w", check_tf]))

  data = fetch(symbol, need_tfs, is_crypto)
  adaptive = _build_adaptive(symbol, data, need_tfs)
  scan = evaluate_triggers(item, data, adaptive)
  return {**item, **scan}


def scan_monitor_queue(
  queue: List[dict],
  is_crypto: bool = True,
  dedupe_symbols: bool = True,
) -> Tuple[List[dict], List[dict]]:
  """
  Scan all queue items. Returns (updated_queue, events).
  Invalidated items are removed from the active queue but logged as events.
  """
  events: List[dict] = []
  updated: List[dict] = []
  data_cache: Dict[str, Tuple[dict, dict]] = {}

  for item in queue:
    symbol = item["symbol"]
    style = item["style"]
    check_tf = item.get("check") or STYLE_CHECK_TF.get(style, "1d")

    if dedupe_symbols and symbol in data_cache:
      data, adaptive = data_cache[symbol]
      scan = evaluate_triggers(item, data, adaptive)
      merged = {**item, **scan}
    else:
      need_tfs = list(dict.fromkeys(["1d", "4h", "1h", "15m", "1w", check_tf]))
      data = fetch(symbol, need_tfs, is_crypto)
      adaptive = _build_adaptive(symbol, data, need_tfs)
      if dedupe_symbols:
        data_cache[symbol] = (data, adaptive)
      scan = evaluate_triggers(item, data, adaptive)
      merged = {**item, **scan}

    event = {
      "ts": merged.get("scanned_at"),
      "symbol": symbol,
      "style": style,
      "prior_status": merged.get("prior_status"),
      "new_status": merged.get("new_status"),
      "triggers_hit": merged.get("triggers_hit", []),
      "upgrade_note": merged.get("upgrade_note"),
      "invalidated": merged.get("invalidated", False),
      "invalidate_reasons": merged.get("invalidate_reasons", []),
      "price": merged.get("price"),
    }
    events.append(event)

    if merged.get("new_status") == "invalidated":
      continue

    merged["status"] = merged["new_status"]
    merged["last_scan"] = merged.get("scanned_at")
    updated.append(merged)

  return updated, events


def append_events(events: List[dict], path: Path = EVENTS_PATH) -> None:
  if not events:
    return
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("a") as f:
    for e in events:
      f.write(json.dumps(e, default=str) + "\n")


def save_scanned_queue(
  queue: List[dict],
  path: str | Path = DEFAULT_QUEUE_PATH,
  events: Optional[List[dict]] = None,
) -> dict:
  """Persist updated queue and optionally log events."""
  if events:
    append_events(events)
  payload = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "queue": queue,
  }
  p = Path(path)
  p.parent.mkdir(parents=True, exist_ok=True)
  with p.open("w") as f:
    json.dump(payload, f, indent=2)
  return payload


def run_monitor_cycle(
  queue_path: str | Path = DEFAULT_QUEUE_PATH,
  is_crypto: bool = True,
) -> dict:
  """One full monitor pass: load → scan → save → return summary."""
  doc = load_monitor_queue(queue_path)
  queue = doc.get("queue", [])
  if not queue:
    return {"scanned": 0, "upgraded": 0, "downgraded": 0, "invalidated": 0, "queue": []}

  updated, events = scan_monitor_queue(queue, is_crypto=is_crypto)
  upgraded = sum(1 for e in events if e.get("prior_status") == "monitor" and e.get("new_status") == "executable")
  downgraded = sum(1 for e in events if e.get("prior_status") == "executable" and e.get("new_status") == "monitor")
  invalidated = sum(1 for e in events if e.get("new_status") == "invalidated")

  save_scanned_queue(updated, queue_path, events)

  return {
    "scanned": len(events),
    "upgraded": upgraded,
    "downgraded": downgraded,
    "invalidated": invalidated,
    "events": events,
    "queue_size": len(updated),
  }
