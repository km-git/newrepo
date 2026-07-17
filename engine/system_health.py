"""System health — aggregate status for continuous testing and ops."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


HEALTH_PATH = Path(os.environ.get("EW_HEALTH_PATH", "output/system/health.json"))


def _ok(check: str, detail: str = "", **extra) -> dict:
  return {"check": check, "ok": True, "detail": detail, **extra}


def _fail(check: str, detail: str = "", **extra) -> dict:
  return {"check": check, "ok": False, "detail": detail, **extra}


def run_health_checks() -> Dict[str, Any]:
  """Non-destructive health probes for E2E system."""
  checks: List[dict] = []

  # Core imports
  try:
    from engine.adaptive import adaptive_pipeline  # noqa: F401
    from engine.limit_orders_export import export_limit_orders  # noqa: F401
    checks.append(_ok("imports", "core pipeline modules load"))
  except Exception as e:
    checks.append(_fail("imports", str(e)))

  # Test count marker
  tests_dir = Path("tests")
  test_files = list(tests_dir.glob("test_*.py")) if tests_dir.exists() else []
  checks.append(_ok("tests", f"{len(test_files)} test modules", count=len(test_files)))

  # Output artifacts
  for name, path in [
    ("metrics", "output/autodream/metrics.json"),
    ("scheduler", "output/autodream/scheduler_state.json"),
    ("limit_csv", "output/latest_limit_orders_all_tf.csv"),
  ]:
    p = Path(path)
    checks.append(_ok(name, "exists") if p.exists() else _fail(name, "missing", path=str(p)))

  # OKF brain
  try:
    from engine.brain_self_improve import improvement_summary
    imp = improvement_summary()
    checks.append(_ok("okf_brain", f"lessons={imp.get('lesson_count', 0)}", **imp))
  except Exception as e:
    checks.append(_fail("okf_brain", str(e)))

  # Execution stack
  try:
    from engine.execution_agent import execution_status
    ex = execution_status()
    checks.append(_ok("execution", f"mode={ex.get('mode')}", **{k: ex.get(k) for k in ("broker", "halted")}))
  except Exception as e:
    checks.append(_fail("execution", str(e)))

  # Data hub
  try:
    from gateway.data_hub import data_hub_enabled
    from gateway.proxy_pool import get_proxy_pool
    checks.append(_ok("data_hub", f"enabled={data_hub_enabled()}", proxies=get_proxy_pool().stats()))
  except Exception as e:
    checks.append(_fail("data_hub", str(e)))

  # Risk halt
  try:
    from engine.risk_ops import is_halted, _load
    state = _load()
    if is_halted():
      checks.append(_fail("risk_halt", state.get("halt_reason", "halted")))
    else:
      checks.append(_ok("risk_halt", "active"))
  except Exception as e:
    checks.append(_fail("risk_halt", str(e)))

  passed = sum(1 for c in checks if c.get("ok"))
  report = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "passed": passed,
    "total": len(checks),
    "healthy": passed == len(checks),
    "checks": checks,
  }
  return report


def save_health(report: Optional[dict] = None) -> str:
  report = report or run_health_checks()
  HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
  HEALTH_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
  return str(HEALTH_PATH)
