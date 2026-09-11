#!/usr/bin/env bash
# Back-compat wrapper — prefer scripts/setup_environment.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$ROOT/scripts/setup_environment.sh" --skip-gh "$@"
