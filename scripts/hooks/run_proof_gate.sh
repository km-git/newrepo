#!/usr/bin/env bash
# Shared proof gate for Kiro hooks, Spec Kit extensions, and CI.
# Usage: run_proof_gate.sh [fast|full]
set -euo pipefail

MODE="${1:-fast}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "[proof-gate] ERROR: missing .venv — run scripts/setup_environment.sh" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

echo "[proof-gate] mode=$MODE root=$ROOT"

FAST_TESTS=(
  tests/test_paper_simulator.py
  tests/test_paper_forward_tracker.py
  tests/test_paper_policy.py
  tests/test_effectiveness_gates.py
)

echo "[proof-gate] pytest subset"
"$PY" -m pytest "${FAST_TESTS[@]}" -q --tb=short

if [[ "$MODE" == "fast" ]]; then
  echo "[proof-gate] fast gate PASS"
  exit 0
fi

echo "[proof-gate] continuous proof loop (LLM-free)"
export EW_IMPROVEMENT_LLM=0 EW_AI_IMPROVEMENT=0 EW_DEEP_RESEARCH=0 EW_BRAIN_SELF_IMPROVE=0
bash "${ROOT}/scripts/run_continuous_proof_loop.sh"

if [[ -f reports/CONTINUOUS_PROOF.md ]]; then
  echo "[proof-gate] --- verdict ---"
  grep -E '^(# |Verdict|PROOF_)' reports/CONTINUOUS_PROOF.md | head -20 || true
fi

echo "[proof-gate] full gate complete"
