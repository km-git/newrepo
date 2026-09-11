#!/usr/bin/env python3
"""Smoke-test Cursor LLM backend — confirms CURSOR_API_KEY and panel routing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from engine.llm_backend import bootstrap_llm_env, credentials_hint, cursor_available, cursor_key_source, llm_backend


def main() -> int:
  info = bootstrap_llm_env()
  print("LLM bootstrap:", json.dumps({**info, "hint": credentials_hint()}, indent=2))

  if not cursor_available():
    print(
      "\nCURSOR_API_KEY not found in this agent session.\n"
      "If you just added it in Cursor Dashboard → Cloud Agents → Secrets:\n"
      "  • Name must be exactly: CURSOR_API_KEY (or EW_CURSOR_API_KEY)\n"
      "  • Start a NEW cloud agent run — secrets do not hot-reload mid-session\n"
      "Or add to workspace/.env (gitignored):\n"
      "  CURSOR_API_KEY=crsr_...\n",
      file=sys.stderr,
    )
    return 1

  print(f"\nKey source: {cursor_key_source()}")
  print(f"Backend: {llm_backend()}")

  if "--live" not in sys.argv:
    print("\nDry check OK. Re-run with --live to call Cursor Cloud Agents API.")
    return 0

  from engine.llm_cursor import call_cursor_advisory

  print("\nCalling Cursor advisory (cheap screen)...")
  out = call_cursor_advisory(
    'DATA:{"sym":"TEST","v":"CONDITIONAL_GO"}\nJSON:',
    "composer-2.5",
    task="screen",
    max_output=120,
  )
  safe = {k: out.get(k) for k in ("available", "stance", "summary", "error", "backend", "model")}
  print(json.dumps(safe, indent=2))
  return 0 if out.get("available") and out.get("stance") else 1


if __name__ == "__main__":
  raise SystemExit(main())
