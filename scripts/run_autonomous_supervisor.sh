#!/usr/bin/env bash
# Supreme 24/7 autonomous supervisor — no user input required.
# Runs: universe scanner + continuous agent + fast autonomous ticks + daily full loop.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

# === Autonomous flags (all on by default) ===
export EW_AUTONOMOUS_OPS="${EW_AUTONOMOUS_OPS:-1}"
export EW_AUTONOMOUS_FAST_INTERVAL="${EW_AUTONOMOUS_FAST_INTERVAL:-1800}"   # 30 min
export EW_AUTONOMOUS_DAILY_INTERVAL="${EW_AUTONOMOUS_DAILY_INTERVAL:-86400}" # 24h
export EW_PR_AUTO_APPROVE="${EW_PR_AUTO_APPROVE:-1}"
export EW_PR_AUTO_MERGE="${EW_PR_AUTO_MERGE:-1}"
export EW_PR_AUTO_RESOLVE_CONFLICTS="${EW_PR_AUTO_RESOLVE_CONFLICTS:-1}"
export EW_PR_MERGE_WITHOUT_PANEL="${EW_PR_MERGE_WITHOUT_PANEL:-1}"
export EW_AUTORESEARCH_AUTO_PROMOTE="${EW_AUTORESEARCH_AUTO_PROMOTE:-1}"
export EW_DEEP_RESEARCH="${EW_DEEP_RESEARCH:-1}"
export EW_WEB_INTEL="${EW_WEB_INTEL:-1}"
export EW_WS_ENABLED="${EW_WS_ENABLED:-1}"
export EW_SOCIAL_INTEL="${EW_SOCIAL_INTEL:-1}"
export EW_AI_IMPROVEMENT="${EW_AI_IMPROVEMENT:-1}"
export EW_IMPROVEMENT_LLM="${EW_IMPROVEMENT_LLM:-1}"
export EW_USE_ALL_CURSOR_MODELS="${EW_USE_ALL_CURSOR_MODELS:-1}"
export EW_CHEAP_FIRST="${EW_CHEAP_FIRST:-1}"
export EW_CURSOR_PRO_ONLY="${EW_CURSOR_PRO_ONLY:-1}"
export EW_ALLOW_OTHER_MODELS="${EW_ALLOW_OTHER_MODELS:-0}"
export EW_USE_CURSOR_API_POOL="${EW_USE_CURSOR_API_POOL:-0}"
export EW_LLM_CHEAP_TARGET_PCT="${EW_LLM_CHEAP_TARGET_PCT:-98}"
export EW_OTHER_MODELS_BUDGET_PCT="${EW_OTHER_MODELS_BUDGET_PCT:-2}"
export EW_OTHER_MODELS_SHAME_PCT="${EW_OTHER_MODELS_SHAME_PCT:-5}"
export EW_LLM_ROUTINE_INTELLIGENCE="${EW_LLM_ROUTINE_INTELLIGENCE:-single}"
export EW_LLM_EW_BYPASS="${EW_LLM_EW_BYPASS:-1}"
export EW_MINIMIZE_GPT="${EW_MINIMIZE_GPT:-1}"
export EW_LLM_BACKEND="${EW_LLM_BACKEND:-cursor}"
export EW_CHEAP_MODEL_RATIO="${EW_CHEAP_MODEL_RATIO:-0.90}"
export EW_CURSOR_MODEL_RATIO="${EW_CURSOR_MODEL_RATIO:-0.98}"
export EW_CURSOR_POOL_GOVERNOR="${EW_CURSOR_POOL_GOVERNOR:-1}"
export EW_CURSOR_FALLBACK="${EW_CURSOR_FALLBACK:-1}"
export EW_CURSOR_MODELS_ONLY="${EW_CURSOR_MODELS_ONLY:-0}"
export EW_USE_OTHER_MODEL_POOL="${EW_USE_OTHER_MODEL_POOL:-1}"
export EW_OTHER_MODELS_BUDGET_PCT="${EW_OTHER_MODELS_BUDGET_PCT:-2}"
export EW_CURSOR_ONLY_SCREEN="${EW_CURSOR_ONLY_SCREEN:-1}"
export EW_MODEL_BUDGET_GOVERNOR="${EW_MODEL_BUDGET_GOVERNOR:-1}"
export EW_PREMIUM_ESCALATION="${EW_PREMIUM_ESCALATION:-smart}"
export EW_MINIMIZE_GPT="${EW_MINIMIZE_GPT:-1}"
export EW_ROUTINE_LLM="${EW_ROUTINE_LLM:-0}"
export EW_CHEAP_PARALLEL_MAX="${EW_CHEAP_PARALLEL_MAX:-4}"
export EW_LLM_EW_BYPASS="${EW_LLM_EW_BYPASS:-1}"
export EW_LLM_INTELLIGENCE="${EW_LLM_INTELLIGENCE:-ensemble}"
export EW_TOOL_AUDIT="${EW_TOOL_AUDIT:-1}"
export EW_ORDERBOOK_ENABLED="${EW_ORDERBOOK_ENABLED:-1}"
export EW_LLM_ADVISORY="${EW_LLM_ADVISORY:-1}"
export EW_OKF_BRAIN_DIR="${EW_OKF_BRAIN_DIR:-output/okf/brain}"
export EW_OKF_BRAIN="${EW_OKF_BRAIN:-1}"
export EW_BRAIN_SELF_IMPROVE="${EW_BRAIN_SELF_IMPROVE:-1}"
export EW_TV_OSS_CONSENSUS="${EW_TV_OSS_CONSENSUS:-1}"
export EW_TV_OSS_EXECUTIVE="${EW_TV_OSS_EXECUTIVE:-1}"
export EW_TV_OSS_EXPLORE="${EW_TV_OSS_EXPLORE:-1}"
export EW_TV_MICROSTRUCTURE="${EW_TV_MICROSTRUCTURE:-1}"
export EW_TV_CYCLES="${EW_TV_CYCLES:-1}"
export EW_DATA_HUB="${EW_DATA_HUB:-1}"
export EW_OHLCV_CHAIN="${EW_OHLCV_CHAIN:-okx,kraken,binance}"
export EW_EXECUTIVE_EXPORT_FILTER="${EW_EXECUTIVE_EXPORT_FILTER:-1}"
export EW_EXECUTIVE_FILTER="${EW_EXECUTIVE_FILTER:-1}"
export EW_EXECUTION_CONSENSUS_LLM="${EW_EXECUTION_CONSENSUS_LLM:-0}"
export EW_UNIVERSE_AUTO_EXECUTE="${EW_UNIVERSE_AUTO_EXECUTE:-1}"
export EW_AUTONOMOUS_UNIVERSE_EXECUTE="${EW_AUTONOMOUS_UNIVERSE_EXECUTE:-0}"
export EW_AUTONOMOUS_BACKTEST="${EW_AUTONOMOUS_BACKTEST:-1}"
export ACCOUNT_EQUITY="${ACCOUNT_EQUITY:-50000}"

mkdir -p output/autonomous output/okf/brain
LOG="${EW_SUPERVISOR_LOG:-output/autonomous/supervisor.log}"
PID_FILE="${EW_SUPERVISOR_PID:-output/autonomous/supervisor.pid}"
echo $$ >"$PID_FILE"

log() { echo "[supervisor] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG"; }

log "started pid=$$ fast=${EW_AUTONOMOUS_FAST_INTERVAL}s daily=${EW_AUTONOMOUS_DAILY_INTERVAL}s"

# Background: universe 1000-pair scanner (if not already running)
if [[ "${EW_SUPERVISOR_START_UNIVERSE:-1}" == "1" ]]; then
  if ! pgrep -f "run_universe_247.py" >/dev/null 2>&1; then
    log "starting universe scanner daemon"
    nohup bash scripts/run_universe_daemon.sh >>output/autodream/universe_247.log 2>&1 &
  fi
fi

# Background: continuous monitor + paper (if not already running)
if [[ "${EW_SUPERVISOR_START_CONTINUOUS:-1}" == "1" ]]; then
  if ! pgrep -f "run_continuous_agent.sh" >/dev/null 2>&1; then
    log "starting continuous agent"
    nohup bash scripts/run_continuous_agent.sh >>output/autodream/continuous_agent.log 2>&1 &
  fi
fi

LAST_DAILY=0
while true; do
  NOW=$(date +%s)

  log "fast tick — learn + research + autoresearch + PR merge"
  python3 -c "
from engine.autonomous_ops import run_autonomous_tick
import json
r = run_autonomous_tick()
print(json.dumps({'ok': r.get('ok'), 'health': r.get('health'), 'phases': list(r.get('phases', {}).keys())}, indent=2))
" 2>&1 | tee -a "$LOG" || log "fast tick failed (continuing)"

  ELAPSED=$((NOW - LAST_DAILY))
  if [[ "$ELAPSED" -ge "${EW_AUTONOMOUS_DAILY_INTERVAL}" ]] || [[ "$LAST_DAILY" -eq 0 && "${EW_SUPERVISOR_DAILY_ON_START:-1}" == "1" ]]; then
    log "daily full loop — pytest + supreme pipeline"
    bash scripts/run_autonomous_daily.sh 2>&1 | tee -a "$LOG" || log "daily loop failed (continuing)"
    LAST_DAILY=$(date +%s)
  fi

  log "sleeping ${EW_AUTONOMOUS_FAST_INTERVAL}s"
  sleep "${EW_AUTONOMOUS_FAST_INTERVAL}"
done
