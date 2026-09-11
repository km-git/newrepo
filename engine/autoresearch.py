"""Decoupled AutoResearch — log strategy/risk experiments; never auto-promote to live."""

from __future__ import annotations

import contextlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from engine.strategy_fitness import composite_fitness, fitness_from_metrics


EXPERIMENT_LOG = Path(os.environ.get("EW_AUTORESEARCH_LOG", "output/autoresearch/experiments.jsonl"))


def autoresearch_enabled() -> bool:
  return os.environ.get("EW_AUTORESEARCH", "1").lower() not in ("0", "false", "no")


def _append(record: dict) -> None:
  EXPERIMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
  with EXPERIMENT_LOG.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, default=str) + "\n")


def _read_log(limit: int = 200) -> List[dict]:
  if not EXPERIMENT_LOG.exists():
    return []
  rows: List[dict] = []
  for line in EXPERIMENT_LOG.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
      continue
    try:
      rows.append(json.loads(line))
    except json.JSONDecodeError:
      continue
  return rows[-limit:]


def propose_experiments() -> List[Dict[str, Any]]:
  """
  Suggest parameter experiments (human or overnight runner applies them).
  Does not mutate production code — env toggles and documented hypotheses only.
  """
  return [
    {
      "id": "wider_sl_floor",
      "hypothesis": "Raise TF min SL 5% → fewer stop-outs, lower win rate",
      "env": {"EW_TF_STOP_MIN_MULT": "1.05"},
      "risk": "low",
    },
    {
      "id": "stricter_execution_consensus",
      "hypothesis": "Block caution stances → fewer paper orders, higher quality",
      "env": {"EW_EXECUTION_BLOCK_CAUTION": "1"},
      "risk": "medium",
    },
    {
      "id": "dynamic_risk_on",
      "hypothesis": "Scale probe size by hist win rate + TV score",
      "env": {"EW_DYNAMIC_RISK": "1"},
      "risk": "low",
    },
    {
      "id": "llm_execution_panel",
      "hypothesis": "Cursor multi-model gate on every executable row",
      "env": {"EW_EXECUTION_CONSENSUS_LLM": "1", "EW_LLM_BACKEND": "cursor"},
      "risk": "token_cost",
    },
  ]


def record_baseline_fitness(note: str = "baseline") -> Dict[str, Any]:
  """Log current metrics fitness as experiment baseline (no env change)."""
  fit = fitness_from_metrics()
  record = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "experiment_id": note,
    "action": "baseline",
    "env_delta": {},
    "fitness": fit,
    "promoted": False,
  }
  _append(record)
  return record


def run_autoresearch_batch(
  *,
  max_experiments: int = 5,
  record_baseline: bool = True,
) -> Dict[str, Any]:
  """
  Log baseline + proposed experiments with current fitness scores.
  Full re-backtest per variant requires a separate overnight batch runner;
  this keeps research decoupled from live trading (Swarm Trader pattern).
  """
  if not autoresearch_enabled():
    return {"skipped": True, "reason": "EW_AUTORESEARCH disabled"}

  out: Dict[str, Any] = {"proposals": [], "logged": []}
  if record_baseline:
    out["logged"].append(record_baseline_fitness("baseline"))

  baseline_fitness = out["logged"][0]["fitness"]["fitness"] if out["logged"] else fitness_from_metrics()["fitness"]

  for prop in propose_experiments()[:max_experiments]:
    entry = {
      "ts": datetime.now(timezone.utc).isoformat(),
      "experiment_id": prop["id"],
      "action": "proposed",
      "hypothesis": prop["hypothesis"],
      "env_delta": prop["env"],
      "risk": prop["risk"],
      "fitness_at_proposal": baseline_fitness,
      "promoted": False,
      "note": "Run batch with env_delta, re-score fitness, compare to baseline before promote",
    }
    _append(entry)
    out["proposals"].append(entry)

  out["baseline_fitness"] = baseline_fitness
  out["log_path"] = str(EXPERIMENT_LOG)
  return out


def latest_experiments_summary(limit: int = 20) -> Dict[str, Any]:
  rows = _read_log(limit)
  if not rows:
    return {"count": 0, "log_path": str(EXPERIMENT_LOG)}
  scored = [r for r in rows if (r.get("fitness") or {}).get("fitness") is not None]
  best = max(scored, key=lambda r: float((r.get("fitness") or {}).get("fitness") or 0)) if scored else rows[-1]
  return {
    "count": len(rows),
    "log_path": str(EXPERIMENT_LOG),
    "latest_id": rows[-1].get("experiment_id"),
    "best_fitness": (best.get("fitness") or {}).get("fitness"),
    "best_id": best.get("experiment_id"),
    "pending_promote": [r["experiment_id"] for r in rows if r.get("action") == "proposed" and not r.get("promoted")],
  }


@contextlib.contextmanager
def env_overlay(delta: Dict[str, str]) -> Iterator[None]:
  """Temporarily apply env toggles for isolated experiment trials."""
  saved: Dict[str, Optional[str]] = {}
  for key, value in delta.items():
    saved[key] = os.environ.get(key)
    os.environ[key] = str(value)
  try:
    yield
  finally:
    for key, prior in saved.items():
      if prior is None:
        os.environ.pop(key, None)
      else:
        os.environ[key] = prior


def find_latest_analysis_json(output_dir: str = "output") -> Optional[Path]:
  root = Path(output_dir)
  if not root.is_dir():
    return None
  patterns = ("top*_analysis_*.json", "top50_analysis_*.json")
  cands: List[Path] = []
  for pat in patterns:
    cands.extend(root.glob(pat))
  if not cands:
    return None
  return max(cands, key=lambda p: p.stat().st_mtime)


def load_analysis_results(path: Path) -> List[dict]:
  data = json.loads(path.read_text(encoding="utf-8"))
  if isinstance(data, list):
    return data
  if isinstance(data, dict):
    for key in ("results", "pairs", "instruments"):
      chunk = data.get(key)
      if isinstance(chunk, list):
        return chunk
  raise ValueError(f"unsupported analysis JSON shape: {path}")


def export_strategy_proxy(results: List[dict]) -> Dict[str, Any]:
  """
  Fast fitness proxy from cached batch analysis (no exchange fetch).
  Scores executable breadth, stop quality, and readiness without mutating live state.
  """
  from engine.limit_orders_export import build_all_limit_orders

  rows = build_all_limit_orders(results)
  primaries = [r for r in rows if r.get("row_type", "primary") == "primary" and r.get("status") != "error"]
  executable = [r for r in primaries if r.get("gtc_tier") == "executable"]
  monitor = [r for r in primaries if r.get("gtc_tier") == "monitor"]

  stop_pcts: List[float] = []
  readiness: List[float] = []
  for r in executable:
    try:
      wae = float(r["wae"])
      sl = float(r["stop_loss"])
      if wae > 0:
        stop_pcts.append(abs(wae - sl) / wae * 100.0)
    except (KeyError, TypeError, ValueError):
      pass
    try:
      readiness.append(float(r.get("readiness_score") or 0))
    except (TypeError, ValueError):
      pass

  n = len(primaries) or 1
  exec_rate = len(executable) / n
  mon_rate = len(monitor) / n
  median_stop = sorted(stop_pcts)[len(stop_pcts) // 2] if stop_pcts else None
  mean_ready = sum(readiness) / len(readiness) if readiness else None

  # Proxy maps to composite_fitness scale (no closed-trade Sharpe yet).
  proxy_return = exec_rate * 25.0 + mon_rate * 5.0
  proxy_win = min(0.7, 0.4 + exec_rate * 0.35)
  proxy_sharpe = min(2.0, exec_rate * 2.5 + (mean_ready or 0) * 0.5)
  fit = composite_fitness(
    win_rate=proxy_win,
    return_pct=proxy_return,
    sharpe=proxy_sharpe,
    sortino=proxy_sharpe * 1.1,
    profit_factor=1.0 + exec_rate,
  )
  fit["proxy"] = True
  fit["export_stats"] = {
    "rows": len(primaries),
    "executable": len(executable),
    "monitor": len(monitor),
    "exec_rate": round(exec_rate, 4),
    "median_stop_pct": round(median_stop, 4) if median_stop is not None else None,
    "mean_readiness": round(mean_ready, 4) if mean_ready is not None else None,
  }
  return fit


def merge_outcome_and_export_fitness(
  outcome_fit: Dict[str, Any],
  export_fit: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
  """Prefer outcome tracker when enough closes; otherwise export proxy."""
  if not export_fit:
    return outcome_fit
  n_trades = int(outcome_fit.get("n_trades") or 0)
  if n_trades >= int(os.environ.get("EW_FITNESS_MIN_TRADES", "5")):
    merged = dict(outcome_fit)
    merged["source"] = "outcomes"
    merged["export_stats"] = export_fit.get("export_stats")
    return merged
  merged = dict(export_fit)
  merged["source"] = "export_proxy"
  merged["outcome_fitness"] = outcome_fit.get("fitness")
  merged["n_trades"] = n_trades
  return merged


def evaluate_experiment(
  experiment_id: str,
  env_delta: Dict[str, str],
  *,
  analysis_path: Optional[Path] = None,
) -> Dict[str, Any]:
  """Score one env experiment against cached analysis + current outcome metrics."""
  path = analysis_path or find_latest_analysis_json()
  export_fit: Optional[Dict[str, Any]] = None
  analysis_used: Optional[str] = None
  walk_forward_fit: Optional[Dict[str, Any]] = None

  with env_overlay(env_delta):
    outcome_fit = fitness_from_metrics()
  if path and path.exists():
    try:
      results = load_analysis_results(path)
      with env_overlay(env_delta):
        export_fit = export_strategy_proxy(results)
        # Re-run paper backtest under env_delta when export rows exist
        try:
          from engine.backtest_runner import run_walk_forward_backtest

          bt = run_walk_forward_backtest(fetch_ohlc=os.environ.get("EW_BACKTEST_FETCH_OHLC", "0") == "1")
          if bt.get("ok"):
            walk_forward_fit = bt.get("fitness")
            export_fit["walk_forward"] = {
              "win_rate": bt.get("win_rate"),
              "return_pct": bt.get("return_pct"),
              "simulated": bt.get("simulated"),
            }
        except Exception as exc:
          export_fit["walk_forward_error"] = str(exc)
      analysis_used = str(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
      export_fit = {"error": str(exc), "proxy": True, "fitness": outcome_fit.get("fitness", 0.0)}
  fitness = merge_outcome_and_export_fitness(outcome_fit, export_fit)
  if walk_forward_fit and walk_forward_fit.get("fitness") is not None:
    # Blend walk-forward fitness when paper backtest ran
    wf_score = float(walk_forward_fit.get("fitness") or 0)
    base_score = float(fitness.get("fitness") or 0)
    fitness["fitness"] = round(0.6 * wf_score + 0.4 * base_score, 4)
    fitness["walk_forward_fitness"] = walk_forward_fit

  record = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "experiment_id": experiment_id,
    "action": "evaluated",
    "env_delta": env_delta,
    "fitness": fitness,
    "analysis_path": analysis_used,
    "promoted": False,
  }
  _append(record)
  return record


def run_autoresearch_eval_loop(
  *,
  max_experiments: Optional[int] = None,
  analysis_path: Optional[str] = None,
  include_baseline: bool = True,
) -> Dict[str, Any]:
  """
  Overnight-style loop: evaluate each proposed env toggle on cached analysis.
  Never promotes to live — append-only log for human review.
  """
  if not autoresearch_enabled():
    return {"skipped": True, "reason": "EW_AUTORESEARCH disabled"}

  path = Path(analysis_path) if analysis_path else find_latest_analysis_json()
  if path is None or not path.exists():
    return {
      "ok": False,
      "error": "no cached analysis JSON in output/ — run top-N batch first",
      "hint": ".venv/bin/python ew_tool.py --top 5 --crypto",
    }

  limit = max_experiments
  if limit is None:
    limit = int(os.environ.get("EW_AUTORESEARCH_MAX", "4"))

  out: Dict[str, Any] = {"ok": True, "analysis_path": str(path), "evaluated": []}
  if include_baseline:
    out["evaluated"].append(evaluate_experiment("baseline_eval", {}, analysis_path=path))

  by_id = {p["id"]: p for p in propose_experiments()}
  for prop in propose_experiments()[:limit]:
    exp_id = prop["id"]
    out["evaluated"].append(
      evaluate_experiment(exp_id, prop["env"], analysis_path=path),
    )

  scores = [
    (e["experiment_id"], float((e.get("fitness") or {}).get("fitness") or 0))
    for e in out["evaluated"]
  ]
  if scores:
    best_id, best_score = max(scores, key=lambda x: x[1])
    out["best"] = {"experiment_id": best_id, "fitness": best_score}
  out["log_path"] = str(EXPERIMENT_LOG)
  out["catalog"] = {k: by_id[k]["hypothesis"] for k in by_id}
  return out


PROMOTED_ENV_PATH = Path(os.environ.get("EW_AUTORESEARCH_ACTIVE_ENV", "output/autoresearch/active_env.json"))


def _promoted_env_path() -> Path:
  return Path(os.environ.get("EW_AUTORESEARCH_ACTIVE_ENV", "output/autoresearch/active_env.json"))


def auto_promote_enabled() -> bool:
  return os.environ.get("EW_AUTORESEARCH_AUTO_PROMOTE", "1").lower() not in ("0", "false", "no")


def auto_promote_best_experiment(eval_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
  """
  Auto-promote best experiment when fitness beats baseline by threshold.
  Writes active env overlay to output/autoresearch/active_env.json (not live keys).
  """
  if not auto_promote_enabled():
    return {"skipped": True, "reason": "EW_AUTORESEARCH_AUTO_PROMOTE off"}

  eval_result = eval_result or run_autoresearch_eval_loop()
  if not eval_result.get("ok"):
    return {"promoted": False, "reason": eval_result.get("error", "eval failed")}

  best = eval_result.get("best") or {}
  best_id = best.get("experiment_id", "")
  best_score = float(best.get("fitness") or 0)

  baseline_scores = [
    float((e.get("fitness") or {}).get("fitness") or 0)
    for e in eval_result.get("evaluated", [])
    if e.get("experiment_id") in ("baseline_eval", "baseline")
  ]
  baseline = baseline_scores[0] if baseline_scores else 0.0
  threshold = float(os.environ.get("EW_AUTORESEARCH_PROMOTE_DELTA", "0.02"))
  min_score = float(os.environ.get("EW_AUTORESEARCH_MIN_FITNESS", "0.35"))

  if best_id in ("baseline_eval", "baseline") or best_score < min_score:
    return {"promoted": False, "reason": "baseline still best or below min fitness", "best": best}

  if best_score < baseline + threshold:
    return {
      "promoted": False,
      "reason": f"improvement {best_score - baseline:.4f} < threshold {threshold}",
      "best": best,
      "baseline": baseline,
    }

  by_id = {p["id"]: p for p in propose_experiments()}
  prop = by_id.get(best_id)
  if not prop:
    return {"promoted": False, "reason": f"unknown experiment {best_id}"}

  env_delta = prop.get("env", {})
  out_path = _promoted_env_path()
  out_path.parent.mkdir(parents=True, exist_ok=True)
  doc = {
    "promoted_at": datetime.now(timezone.utc).isoformat(),
    "experiment_id": best_id,
    "fitness": best_score,
    "baseline_fitness": baseline,
    "env_delta": env_delta,
    "hypothesis": prop.get("hypothesis"),
  }
  out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

  record = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "experiment_id": best_id,
    "action": "auto_promoted",
    "env_delta": env_delta,
    "fitness": {"fitness": best_score},
    "promoted": True,
    "note": f"Auto-promoted: fitness {best_score:.4f} vs baseline {baseline:.4f}",
  }
  _append(record)

  try:
    from engine.brain_self_improve import persist_lesson, self_improve_enabled

    if self_improve_enabled():
      persist_lesson(
        "GLOBAL",
        f"autoresearch promoted {best_id}: {prop.get('hypothesis', '')[:120]}",
        source="autoresearch",
      )
  except Exception:
    pass

  return {"promoted": True, "experiment_id": best_id, "fitness": best_score, "env_path": str(out_path)}
