"""Autodream scheduler — periodic full batch refresh + monitor loop."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from engine.autodream_monitor import DEFAULT_QUEUE_PATH, run_monitor_cycle
from engine.top50_batch import DEFAULT_TFS, run_top_crypto_batch

STATE_PATH = Path("output/autodream/scheduler_state.json")
LATEST_PATHS = Path("output/autodream/latest_paths.json")


def _latest_paths_file(output_dir: str) -> Path:
  return Path(output_dir) / "autodream" / "latest_paths.json"


def _utcnow() -> datetime:
  return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
  return dt.isoformat()


def load_state(path: Path = STATE_PATH) -> dict:
  if not path.exists():
    return {}
  try:
    return json.loads(path.read_text())
  except (json.JSONDecodeError, OSError):
    return {}


def save_state(state: dict, path: Path = STATE_PATH) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(state, indent=2, default=str))


def batch_is_due(
  state: dict,
  batch_interval_sec: int,
  queue_path: Path = DEFAULT_QUEUE_PATH,
) -> bool:
  """True if batch interval elapsed or no queue / never run."""
  if batch_interval_sec <= 0:
    return False
  if not queue_path.exists():
    return True
  last = state.get("last_batch_utc")
  if not last:
    return True
  try:
    elapsed = (_utcnow() - datetime.fromisoformat(last)).total_seconds()
  except ValueError:
    return True
  return elapsed >= batch_interval_sec


def publish_latest(meta: dict, output_dir: str = "output") -> dict:
  """
  Copy timestamped batch exports to stable paths for easy access.
  output/latest_analysis.html, .csv, latest_setups.csv
  """
  out = Path(output_dir)
  out.mkdir(parents=True, exist_ok=True)

  stable = {
    "full_html": str(out / "latest_analysis.html"),
    "full_csv": str(out / "latest_analysis.csv"),
    "setups_csv": str(out / "latest_setups.csv"),
    "setups_complete_csv": str(out / "latest_setups_complete.csv"),
    "setups_html": str(out / "latest_setups.html"),
    "setups_md": "reports/TRADE_SETUPS.md",
  }

  src_html = meta.get("full_html")
  src_csv = meta.get("full_csv")
  src_setups = meta.get("setups_csv")

  if src_html and Path(src_html).exists():
    shutil.copy2(src_html, stable["full_html"])
  if src_csv and Path(src_csv).exists():
    shutil.copy2(src_csv, stable["full_csv"])
  if src_setups and Path(src_setups).exists():
    dst_csv = Path(stable["setups_csv"])
    dst_complete = Path(stable["setups_complete_csv"])
    if Path(src_setups).resolve() != dst_csv.resolve():
      shutil.copy2(src_setups, dst_csv)
    if Path(src_setups).resolve() != dst_complete.resolve():
      shutil.copy2(src_setups, dst_complete)

  setups_html_src = Path("output/latest_setups.html")
  if setups_html_src.exists():
    dst = Path(stable["setups_html"])
    if setups_html_src.resolve() != dst.resolve():
      shutil.copy2(setups_html_src, dst)

  # setups markdown written by export_all_reports; ensure reports path exists in doc
  setups_md = Path("reports/TRADE_SETUPS.md")
  if setups_md.exists():
    stable["setups_md"] = str(setups_md.resolve())

  paths_doc = {
    "updated": _iso(_utcnow()),
    "batch_timestamp": meta.get("timestamp_utc"),
    "pairs_count": meta.get("pairs_count"),
    "full_html": stable["full_html"],
    "full_csv": stable["full_csv"],
    "setups_csv": stable["setups_csv"],
    "setups_complete_csv": stable.get("setups_complete_csv"),
    "setups_html": stable.get("setups_html"),
    "setups_md": stable.get("setups_md"),
    "outcomes_csv": meta.get("outcomes_csv"),
    "detailed_csv": meta.get("detailed_csv"),
    "json": meta.get("json"),
    "monitor_queue": meta.get("monitor_queue"),
    "by_verdict": meta.get("by_verdict"),
  }

  latest_file = _latest_paths_file(output_dir)
  latest_file.parent.mkdir(parents=True, exist_ok=True)
  latest_file.write_text(json.dumps(paths_doc, indent=2))
  return paths_doc


def run_batch_refresh(
  n: int = 50,
  output_dir: str = "output",
  quote: str = "USDT",
  tfs: Optional[list] = None,
) -> dict:
  """Run full top-N batch and publish stable latest_* paths."""
  meta = run_top_crypto_batch(n=n, tfs=tfs or DEFAULT_TFS, output_dir=output_dir, quote=quote)
  latest = publish_latest(meta, output_dir=output_dir)
  meta["latest"] = latest
  return meta


def run_scheduler_cycle(
  *,
  batch_n: int = 50,
  batch_interval_sec: int = 3600,
  output_dir: str = "output",
  quote: str = "USDT",
  queue_path: str | Path = DEFAULT_QUEUE_PATH,
  is_crypto: bool = True,
  force_batch: bool = False,
  skip_monitor: bool = False,
) -> dict:
  """
  One scheduler tick:
  1. Run full batch if due (or forced)
  2. Run monitor queue scan (unless skipped)
  """
  state = load_state()
  queue_path = Path(queue_path)
  result: Dict[str, Any] = {
    "batch_ran": False,
    "batch": None,
    "monitor": None,
    "latest": state.get("latest"),
  }

  run_batch = force_batch or (
    batch_interval_sec > 0 and batch_is_due(state, batch_interval_sec, queue_path)
  )
  if run_batch:
    print(f"[scheduler] running top-{batch_n} batch refresh")
    meta = run_batch_refresh(n=batch_n, output_dir=output_dir, quote=quote)
    state["last_batch_utc"] = _iso(_utcnow())
    state["latest"] = meta.get("latest")
    state["last_batch_meta"] = {
      "pairs_count": meta.get("pairs_count"),
      "full_html": meta.get("full_html"),
      "by_verdict": meta.get("by_verdict"),
    }
    result["batch_ran"] = True
    result["batch"] = meta
    result["latest"] = meta.get("latest")

  if not skip_monitor:
    monitor = run_monitor_cycle(queue_path=queue_path, is_crypto=is_crypto)
    state["last_monitor_utc"] = _iso(_utcnow())
    state["last_monitor_summary"] = {
      "scanned": monitor.get("scanned"),
      "upgraded": monitor.get("upgraded"),
      "invalidated": monitor.get("invalidated"),
      "queue_size": monitor.get("queue_size"),
    }
    result["monitor"] = monitor

  save_state(state)
  return result
