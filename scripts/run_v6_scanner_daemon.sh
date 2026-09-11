#!/usr/bin/env bash
# V6 scanner daemon — unified with universe_scanner (835 pairs, 6 TFs, 24/7).
set -euo pipefail
cd "$(dirname "$0")/.."
export EW_V6_SETUP="${EW_V6_SETUP:-1}"
export EW_SCANNER_INCLUDE_SWAP="${EW_SCANNER_INCLUDE_SWAP:-1}"
export UNIVERSE_SIZE="${EW_SCANNER_PAIRS:-1000}"
export CHUNK_SIZE="${EW_SCANNER_CHUNK:-50}"
export TICK_INTERVAL="${EW_V6_CHUNK_INTERVAL:-1800}"
export ACCOUNT_EQUITY="${ACCOUNT_EQUITY:-50000}"
export USDT_D_PCT="${USDT_D_PCT:-8.2}"
export EW_PAPER_AFTER_BATCH="${EW_PAPER_AFTER_BATCH:-0}"
exec python3 scripts/run_universe_247.py "$@"
