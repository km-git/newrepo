#!/usr/bin/env bash
# 24/7 universe scanner: 1000 pairs, 6 timeframes, chunked rotation.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

export UNIVERSE_SIZE="${UNIVERSE_SIZE:-1000}"
export CHUNK_SIZE="${CHUNK_SIZE:-25}"
export TICK_INTERVAL="${TICK_INTERVAL:-300}"
export UNIVERSE_PAPER_MAX="${UNIVERSE_PAPER_MAX:-150}"

exec python3 scripts/run_universe_247.py "$@"
