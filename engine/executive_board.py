"""Executive trade board — always surface ranked actionable pairs × timeframes."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from engine.accurate_setups import (
  STYLE_TF,
  _primary_blocker,
  _stop_ok,
  score_setup_accuracy,
)

BOARD_PATH = Path("output/autodream/executive_board.json")
BOARD_CSV_PATH = Path("output/latest_executive_board.csv")

# Minimum executive score to appear on the board (geometry must pass)
MIN_BOARD_SCORE = 15
DEFAULT_PICKS_PER_TF = 5
DEFAULT_PICKS_TOTAL = 30
BOARD_TIMEFRAMES = ("15m", "1h", "4h", "1d", "1w")
# 4h is context-only in outcomes — anchor entries from day_trade or swing
CONTEXT_TF_ANCHOR_STYLE = ("day_trade", "swing")


def _baseline_score(setup: dict, style: str) -> int:
  """Floor score so every geometry-valid setup can be ranked."""
  if not _stop_ok(setup, style):
    return 0
  score = 12
  readiness = int(setup.get("readiness_score") or 0)
  score += min(20, readiness // 3)
  if setup.get("status") == "monitor":
    score += 10
  elif setup.get("status") == "executable":
    score += 18
  rr = None
  targets = setup.get("targets") or []
  if len(targets) > 1:
    rr = targets[1].get("rr")
  if rr is not None:
    try:
      score += min(8, int(float(rr)))
    except (TypeError, ValueError):
      pass
  return score


def _oos_score(setup: dict) -> Tuple[float, str]:
  oos = setup.get("oos_win_rate")
  n = int(setup.get("oos_trades") or 0)
  if n >= 3 and oos is not None:
    wr = float(oos)
    if wr >= 0.65:
      return 25, f"OOS {wr:.0%} ({n})"
    if wr >= 0.55:
      return 18, f"OOS {wr:.0%} ({n})"
    if wr >= 0.50:
      return 10, f"OOS {wr:.0%} ({n})"
    return 4, f"OOS {wr:.0%} ({n})"
  if setup.get("autodream_verdict") == "validated":
    return 6, "validated hist"
  return 0, "insufficient OOS"


def _executive_action(setup: dict, exec_score: int, blocker: str) -> Tuple[str, int, str]:
  """
  Returns (action, position_size_pct, playbook_line).
  Never returns SKIP — executive always routes to a plan.
  """
  status = setup.get("status")
  tier = setup.get("execution_tier", "none")
  oos = setup.get("oos_win_rate")
  oos_n = int(setup.get("oos_trades") or 0)
  wave_valid = bool(setup.get("wave_valid"))
  wave_partial = bool(setup.get("wave_partial"))

  if status == "executable" and setup.get("oos_gate") == "passed":
    size = 100 if tier == "full" else 50
    return "EXECUTE_NOW", size, "All gates passed — execute per setup tier"

  if status == "executable":
    return "EXECUTE_CAUTION", 35, "Executable label but OOS pending — reduced size"

  if exec_score >= 75 and oos_n >= 3 and oos is not None and float(oos) >= 0.55:
    size = 75 if wave_valid else 40
    return "EXECUTE_NOW", size, "Executive override: strong OOS + composite score"

  if exec_score >= 62 and (wave_valid or wave_partial) and blocker != "broken_geometry":
    return "SCALE_IN", 40, "Scale in 25-40% — partial/valid impulse, await full confirm"

  if exec_score >= 55 and setup.get("autodream_verdict") == "validated":
    return "STANDBY_LIMIT", 30, "Validated edge — limit at entry zone, confirm rejection"

  if exec_score >= 40 and blocker in ("await_impulse_or_zone", "conditional", "oos_insufficient", "none"):
    return "WATCH_ALERT", 15, "Conditional — alert on zone touch + indicator alignment"

  if exec_score >= MIN_BOARD_SCORE and blocker == "rr_below_min":
    return "WATCH_SPECULATIVE", 10, "R:R below style min — paper only or scalp partial TP"

  return "WATCH_ONLY", 10, "Monitor — lowest executive tier, no live size until upgrade"


def executive_setup_score(
  setup: dict,
  style: str,
  symbol_bonus: int = 0,
) -> Tuple[int, List[str]]:
  """Composite executive score 0–100."""
  if not setup or not _stop_ok(setup, style):
    return 0, ["broken_geometry"]

  acc, acc_tier, acc_tags = score_setup_accuracy(setup, style)
  tags = list(acc_tags)
  score = acc

  oos_pts, oos_note = _oos_score(setup)
  score += oos_pts
  if oos_note:
    tags.append(oos_note)

  readiness = int(setup.get("readiness_score") or 0)
  if readiness >= 70:
    score += 8
  elif readiness >= 55:
    score += 4

  if setup.get("wave_valid"):
    score += 10
    tags.append("impulse_valid")
  elif setup.get("wave_partial"):
    score += 6
    tags.append("impulse_partial")

  if setup.get("status") == "executable":
    score += 12

  ex_verdict = setup.get("_executive_verdict", "")
  if ex_verdict in ("GO", "CONDITIONAL_GO"):
    score += 5
  elif ex_verdict == "STAGED_GO":
    score += 3

  if symbol_bonus:
    score += symbol_bonus
    tags.append(f"multi_tf+{symbol_bonus}")

  blocker = _primary_blocker(setup, style)
  if blocker == "oos_below_floor":
    score -= 8
  elif blocker == "invalid_impulse" and not setup.get("wave_partial"):
    score -= 5

  floor = _baseline_score(setup, style)
  return min(100, max(floor, score)), tags


def _score_4h_wave(wave: dict) -> Tuple[int, List[str]]:
  """Score 4h Elliott context for executive routing (no native 4h style setup)."""
  if not wave or wave.get("status") != "ok":
    return 0, ["no_4h_data"]
  tags: List[str] = []
  score = 10
  struct = str(wave.get("structure") or "")
  if wave.get("impulse_valid"):
    score += 28
    tags.append("4h_impulse_valid")
  elif wave.get("impulse_partial"):
    score += 16
    tags.append("4h_impulse_partial")
  elif "impulse_5" in struct:
    score += 18
    tags.append("4h_impulse_label")
  elif struct == "abc_correction":
    score += 12
    tags.append("4h_abc")
  elif struct == "ending_diagonal":
    score += 14
    tags.append("4h_diagonal")
  elif "invalid_impulse" in struct:
    score += 4
    tags.append("4h_invalid_impulse")
  else:
    score += 6
    tags.append(struct[:24] or "4h_unclassified")

  if wave.get("direction") in ("BULL", "BEAR"):
    score += 5
  return min(55, score), tags


def _build_4h_context_rows(results: List[dict], scored: List[dict]) -> List[dict]:
  """Synthesize ranked 4h context picks anchored to nearest executable style."""
  best_by_sym: Dict[str, dict] = {}
  for row in scored:
    sym = row["symbol"]
    if sym not in best_by_sym or row["executive_score"] > best_by_sym[sym]["executive_score"]:
      best_by_sym[sym] = row
  rows: List[dict] = []
  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    wave = (r.get("step2_wave_structure") or {}).get("4h")
    ctx_score, ctx_tags = _score_4h_wave(wave or {})
    if ctx_score < 8:
      continue

    anchor = None
    anchor_style = None
    setups = (r.get("step8_outcomes") or {}).get("setups") or {}
    for style in CONTEXT_TF_ANCHOR_STYLE:
      s = setups.get(style)
      if s and _stop_ok(s, style):
        anchor = s
        anchor_style = style
        break
    if not anchor:
      continue

    base = best_by_sym.get(sym)
    exec_score = min(100, (base["executive_score"] if base else 35) + ctx_score)
    targets = anchor.get("targets") or []
    entry_d = anchor.get("entry") or {}
    stop = anchor.get("stop_loss") or {}
    direction = anchor.get("direction")
    wave_dir = wave.get("direction")
    if wave_dir == "BULL" and direction == "LONG":
      exec_score = min(100, exec_score + 3)
    elif wave_dir == "BEAR" and direction == "SHORT":
      exec_score = min(100, exec_score + 3)

    row = {
      "symbol": sym,
      "style": anchor_style,
      "timeframe": "4h",
      "direction": direction,
      "executive_score": exec_score,
      "accuracy_tier": base.get("accuracy_tier", "C") if base else "C",
      "pipeline_status": anchor.get("status"),
      "execution_tier": anchor.get("execution_tier", ""),
      "readiness_score": anchor.get("readiness_score"),
      "wave_structure": wave.get("structure"),
      "wave_valid": wave.get("impulse_valid"),
      "wave_partial": wave.get("impulse_partial"),
      "oos_win_rate": anchor.get("oos_win_rate"),
      "oos_trades": anchor.get("oos_trades"),
      "entry": entry_d.get("anchor"),
      "entry_order": entry_d.get("order_type", "limit"),
      "stop_loss": stop.get("price"),
      "stop_pct": stop.get("distance_pct"),
      "tp1": targets[0]["price"] if targets else None,
      "tp2": targets[1]["price"] if len(targets) > 1 else None,
      "rr_tp2": targets[1]["rr"] if len(targets) > 1 else None,
      "primary_blocker": _primary_blocker(anchor, anchor_style),
      "tags": ", ".join(ctx_tags + (["4h_context"])),
      "executive_verdict": (r.get("executive_decision") or {}).get("verdict"),
      "consensus": (r.get("step6_wave_consensus") or {}).get("consensus_direction"),
      "agreement_pct": (r.get("step6_wave_consensus") or {}).get("agreement_pct"),
      "honest_reason": f"4h context: {wave.get('structure', '')}"[:160],
      "autodream_verdict": anchor.get("autodream_verdict"),
      "paper_outcome": anchor.get("paper_outcome"),
      "is_4h_context": True,
    }
    setup_match = dict(anchor)
    setup_match["_executive_verdict"] = row["executive_verdict"]
    action, size, playbook = _executive_action(
      setup_match, exec_score, row["primary_blocker"]
    )
    if action == "WATCH_ONLY" and exec_score >= 40:
      action, size, playbook = "WATCH_ALERT", 15, "4h context — alert on structure break + zone"
    row["executive_action"] = action
    row["position_size_pct"] = size
    row["playbook"] = playbook
    rows.append(row)

  rows.sort(key=lambda x: (-x["executive_score"], x["symbol"]))
  return rows


def resolve_accurate_pairs_timeframes(
  results: List[dict],
  picks_per_tf: int = DEFAULT_PICKS_PER_TF,
  max_total: int = DEFAULT_PICKS_TOTAL,
) -> dict:
  """
  Executive entry point — always returns ranked accurate pairs × timeframes.
  Never empty-handed: primary styles + 4h context + portfolio overflow.
  """
  return build_executive_board(results, picks_per_tf=picks_per_tf, max_total=max_total)


def _multi_tf_bonus(by_symbol: Dict[str, List[dict]]) -> Dict[str, int]:
  """Reward symbols with aligned direction across multiple timeframes."""
  bonus: Dict[str, int] = {}
  for sym, items in by_symbol.items():
    dirs = Counter(i["direction"] for i in items if i.get("executive_score", 0) >= 40)
    if not dirs:
      continue
    top_dir, top_n = dirs.most_common(1)[0]
    if top_n >= 3:
      bonus[sym] = 8
    elif top_n >= 2:
      bonus[sym] = 4
  return bonus


def _flatten_setups(results: List[dict]) -> List[dict]:
  rows: List[dict] = []
  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    ex = r.get("executive_decision") or {}
    cons = r.get("step6_wave_consensus") or {}
    for style, setup in (r.get("step8_outcomes") or {}).get("setups", {}).items():
      if not setup:
        continue
      setup = dict(setup)
      setup["_executive_verdict"] = ex.get("verdict", "")
      setup["_symbol"] = sym
      setup["_style"] = style
      setup["_consensus"] = cons.get("consensus_direction")
      setup["_agreement"] = cons.get("agreement_pct")
      rows.append(setup)
  return rows


def build_executive_board(
  results: List[dict],
  picks_per_tf: int = DEFAULT_PICKS_PER_TF,
  max_total: int = DEFAULT_PICKS_TOTAL,
  min_score: int = MIN_BOARD_SCORE,
) -> dict:
  """
  Executive solution board — always returns ranked picks per timeframe.
  Like a desk PM: never empty-handed; routes every top idea to a plan.
  """
  flat = _flatten_setups(results)
  by_symbol: Dict[str, List[dict]] = defaultdict(list)

  scored: List[dict] = []
  for setup in flat:
    sym = setup["_symbol"]
    style = setup["_style"]
    if not _stop_ok(setup, style):
      continue
    entry = (setup.get("entry") or {}).get("anchor")
    if entry is not None:
      try:
        if float(entry) <= 0:
          continue
      except (TypeError, ValueError):
        pass

    score, tags = executive_setup_score(setup, style, 0)
    if score < min_score and _baseline_score(setup, style) < min_score:
      continue

    targets = setup.get("targets") or []
    entry_d = setup.get("entry") or {}
    stop = setup.get("stop_loss") or {}
    blocker = _primary_blocker(setup, style)
    _, acc_tier, _ = score_setup_accuracy(setup, style)

    row = {
      "symbol": sym,
      "style": style,
      "timeframe": STYLE_TF.get(style, setup.get("timeframe", "")),
      "direction": setup.get("direction"),
      "executive_score": score,
      "accuracy_tier": acc_tier,
      "pipeline_status": setup.get("status"),
      "execution_tier": setup.get("execution_tier", ""),
      "readiness_score": setup.get("readiness_score"),
      "wave_structure": setup.get("wave_structure"),
      "wave_valid": setup.get("wave_valid"),
      "wave_partial": setup.get("wave_partial"),
      "oos_win_rate": setup.get("oos_win_rate"),
      "oos_trades": setup.get("oos_trades"),
      "entry": entry_d.get("anchor"),
      "entry_order": entry_d.get("order_type", "limit"),
      "stop_loss": stop.get("price"),
      "stop_pct": stop.get("distance_pct"),
      "tp1": targets[0]["price"] if targets else None,
      "tp2": targets[1]["price"] if len(targets) > 1 else None,
      "rr_tp2": targets[1]["rr"] if len(targets) > 1 else None,
      "primary_blocker": blocker,
      "tags": ", ".join(tags),
      "executive_verdict": setup.get("_executive_verdict"),
      "consensus": setup.get("_consensus"),
      "agreement_pct": setup.get("_agreement"),
      "honest_reason": (setup.get("honest_reason") or "")[:160],
      "autodream_verdict": setup.get("autodream_verdict"),
      "paper_outcome": setup.get("paper_outcome"),
    }
    by_symbol[sym].append(row)
    scored.append(row)

  mtf_bonus = _multi_tf_bonus(by_symbol)
  for row in scored:
    sym = row["symbol"]
    style = row["style"]
    setup_raw = next(
      s for s in flat if s["_symbol"] == sym and s["_style"] == style
    )
    bonus = mtf_bonus.get(sym, 0)
    if bonus:
      row["executive_score"] = min(100, row["executive_score"] + bonus)
      row["tags"] = row["tags"] + f", multi_tf+{bonus}"

  ctx_4h = _build_4h_context_rows(results, scored)

  scored.sort(key=lambda x: (-x["executive_score"], x["symbol"], x["style"]))

  for row in scored:
    setup_match = next(
      (s for s in flat if s["_symbol"] == row["symbol"] and s["_style"] == row["style"]),
      {},
    )
    action, size, playbook = _executive_action(
      setup_match, row["executive_score"], row["primary_blocker"]
    )
    row["executive_action"] = action
    row["position_size_pct"] = size
    row["playbook"] = playbook

  # Guaranteed picks per timeframe
  picks: List[dict] = []
  picked_keys: set[tuple[str, str]] = set()
  by_tf: Dict[str, List[dict]] = defaultdict(list)
  for row in scored:
    by_tf[row["timeframe"]].append(row)

  by_tf["4h"] = ctx_4h

  for tf in BOARD_TIMEFRAMES:
    pool = by_tf.get(tf, [])
    for row in pool[:picks_per_tf]:
      key = (row["symbol"], row["style"] if tf != "4h" else "4h")
      if key in picked_keys:
        continue
      row = dict(row)
      row["board_slot"] = f"{tf}_top"
      row["is_board_pick"] = True
      picks.append(row)
      picked_keys.add(key)

  # Fill to max_total with highest remaining scores (incl. 4h context)
  overflow = sorted(
    scored + [r for r in ctx_4h if (r["symbol"], "4h") not in picked_keys],
    key=lambda x: (-x["executive_score"], x["symbol"]),
  )
  for row in overflow:
    if len(picks) >= max_total:
      break
    key = (row["symbol"], "4h" if row.get("is_4h_context") else row["style"])
    if key in picked_keys:
      continue
    row = dict(row)
    row["board_slot"] = "portfolio"
    row["is_board_pick"] = True
    picks.append(row)
    picked_keys.add(key)

  # If a TF is empty, force best available (lower bar)
  for tf in BOARD_TIMEFRAMES:
    if any(p["timeframe"] == tf for p in picks):
      continue
    pool = ctx_4h if tf == "4h" else [r for r in scored if r["timeframe"] == tf]
    fallback = sorted(pool, key=lambda x: -x["executive_score"])
    if fallback:
      row = dict(fallback[0])
      row["board_slot"] = f"{tf}_fallback"
      row["is_board_pick"] = True
      row["executive_action"] = "WATCH_ONLY"
      row["playbook"] = f"Fallback {tf} — weakest TF coverage; paper only"
      picks.append(row)
      picked_keys.add((row["symbol"], row["style"] if tf != "4h" else "4h"))

  picks.sort(key=lambda x: (
    {"EXECUTE_NOW": 0, "EXECUTE_CAUTION": 1, "SCALE_IN": 2, "STANDBY_LIMIT": 3,
     "WATCH_ALERT": 4, "WATCH_SPECULATIVE": 5, "WATCH_ONLY": 6}.get(x["executive_action"], 9),
    -x["executive_score"],
  ))

  by_action = Counter(p["executive_action"] for p in picks)
  by_tf_out = Counter(p["timeframe"] for p in picks)

  return {
    "updated": datetime.now(timezone.utc).isoformat(),
    "total_scored": len(scored),
    "board_picks": len(picks),
    "picks_per_tf": picks_per_tf,
    "by_action": dict(by_action),
    "by_timeframe": dict(by_tf_out),
    "picks": picks,
    "all_ranked": scored[:50],
  }


def save_executive_board(board: dict, json_path: Path = BOARD_PATH, csv_path: Path = BOARD_CSV_PATH) -> dict:
  json_path.parent.mkdir(parents=True, exist_ok=True)
  json_path.write_text(json.dumps(board, indent=2, default=str))

  picks = board.get("picks", [])
  if picks:
    keys = list(picks[0].keys())
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
      w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
      w.writeheader()
      w.writerows(picks)
  return {"json": str(json_path), "csv": str(csv_path)}


def apply_board_to_results(results: List[dict], board: dict) -> List[dict]:
  """Stamp executive picks back onto step8 outcomes."""
  pick_map = {(p["symbol"], p["style"]): p for p in board.get("picks", [])}
  for r in results:
    if r.get("status") == "incomplete":
      continue
    sym = r["symbol"]
    best_pick = None
    for style, setup in (r.get("step8_outcomes") or {}).get("setups", {}).items():
      pick = pick_map.get((sym, style))
      if pick:
        setup["executive_board"] = {
          "action": pick["executive_action"],
          "score": pick["executive_score"],
          "size_pct": pick["position_size_pct"],
          "playbook": pick["playbook"],
          "board_slot": pick.get("board_slot"),
        }
        if best_pick is None or pick["executive_score"] > best_pick.get("executive_score", 0):
          best_pick = pick
    if best_pick:
      oc = r.setdefault("step8_outcomes", {})
      oc["executive_pick"] = {
        "symbol": sym,
        "style": best_pick["style"],
        "timeframe": best_pick["timeframe"],
        "action": best_pick["executive_action"],
        "direction": best_pick["direction"],
        "score": best_pick["executive_score"],
        "size_pct": best_pick["position_size_pct"],
        "playbook": best_pick["playbook"],
      }
  return results
