#!/usr/bin/env bash
# 24/7 universe scanner: 1000 pairs, 6 timeframes, chunked rotation.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

export UNIVERSE_SIZE="${UNIVERSE_SIZE:-1000}"
export CHUNK_SIZE="${CHUNK_SIZE:-25}"
export TICK_INTERVAL="${TICK_INTERVAL:-300}"
export UNIVERSE_PAPER_MAX="${UNIVERSE_PAPER_MAX:-150}"

# Cursor-hosted multi-model AI improvement (cheap first, escalate when needed)
export EW_LLM_BACKEND="${EW_LLM_BACKEND:-cursor}"
export EW_AI_IMPROVEMENT="${EW_AI_IMPROVEMENT:-1}"
export EW_IMPROVEMENT_LLM="${EW_IMPROVEMENT_LLM:-1}"
export EW_USE_ALL_CURSOR_MODELS="${EW_USE_ALL_CURSOR_MODELS:-1}"
export EW_LLM_ADVISORY="${EW_LLM_ADVISORY:-1}"
export EW_UNIVERSE_LLM_MAX="${EW_UNIVERSE_LLM_MAX:-3}"
export EW_LLM_INTELLIGENCE="${EW_LLM_INTELLIGENCE:-ensemble}"
export EW_USE_GROK_HIGH="${EW_USE_GROK_HIGH:-1}"

exec python3 scripts/run_universe_247.py "$@"
