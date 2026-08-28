#!/usr/bin/env bash
# Supreme daily autonomous loop: test → learn → research → improve → PR merge → OKF.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
LOG_DIR="${EW_AUTONOMOUS_LOG_DIR:-output/autonomous/daily}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/run_${STAMP}.log"
mkdir -p "$LOG_DIR"

export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
export EW_WEB_INTEL="${EW_WEB_INTEL:-1}"
export EW_WS_ENABLED="${EW_WS_ENABLED:-1}"
export EW_SOCIAL_INTEL="${EW_SOCIAL_INTEL:-1}"
export EW_DEEP_RESEARCH="${EW_DEEP_RESEARCH:-1}"
export EW_OKF_BRAIN="${EW_OKF_BRAIN:-1}"
export EW_BRAIN_SELF_IMPROVE="${EW_BRAIN_SELF_IMPROVE:-1}"
export EW_BRAIN_CONSENSUS="${EW_BRAIN_CONSENSUS:-1}"
export EW_IMPACT_DISCOVERY="${EW_IMPACT_DISCOVERY:-1}"
export EW_SOCIAL_VALIDATION="${EW_SOCIAL_VALIDATION:-1}"
export EW_AI_IMPROVEMENT="${EW_AI_IMPROVEMENT:-1}"
export EW_IMPROVEMENT_LLM="${EW_IMPROVEMENT_LLM:-1}"
export EW_USE_ALL_CURSOR_MODELS="${EW_USE_ALL_CURSOR_MODELS:-1}"
export EW_AUTORESEARCH_AUTO_PROMOTE="${EW_AUTORESEARCH_AUTO_PROMOTE:-1}"
export EW_HEALTH_REQUIRE_ARTIFACTS=0
export EW_GOAL_MODE_AUTORESEARCH=0
export EW_OKF_BRAIN_DIR="${EW_OKF_BRAIN_DIR:-output/okf/brain}"
export EW_LLM_BACKEND="${EW_LLM_BACKEND:-cursor}"

exec > >(tee -a "$LOG") 2>&1
echo "[autonomous] started $(date -u +%Y-%m-%dT%H:%M:%SZ) log=$LOG"

if [[ "${EW_AUTONOMOUS_SKIP_TESTS:-0}" != "1" ]]; then
  echo "=== Phase 1: full test suite ==="
  "$PY" -m pytest tests/ -q --tb=line
else
  echo "=== Phase 1: tests skipped (EW_AUTONOMOUS_SKIP_TESTS) ==="
fi

echo "=== Phase 2: improvement + OKF learn + AI models ==="
"$PY" -c "
import json
from engine.improvement_cycle import run_improvement_cycle
r = run_improvement_cycle(is_crypto=True, persist_okf=True, use_llm=True)
print(json.dumps({
  'skipped': r.get('skipped'),
  'resolved': (r.get('metrics') or {}).get('last_resolved'),
  'open_count': (r.get('metrics') or {}).get('open_count'),
  'healthy': (r.get('health') or {}).get('healthy'),
  'ai': (r.get('ai_improvement') or {}).get('consensus_stance'),
}, indent=2))
"

echo "=== Phase 2b: deep research (web + WS + social + AI) ==="
"$PY" -c "
import json
from engine.deep_research import run_deep_research
r = run_deep_research(use_ai=True)
print(json.dumps({'skipped': r.get('skipped'), 'ai': (r.get('ai_synthesis') or {}).get('stance')}, indent=2))
" || echo "[autonomous] deep research skipped: $?"

echo "=== Phase 3: autoresearch (top-N batch + eval) ==="
EW_NIGHTLY_BATCH_N="${EW_NIGHTLY_BATCH_N:-15}" bash scripts/run_nightly_autoresearch.sh || echo "[autonomous] autoresearch phase failed (continuing): $?"

echo "=== Phase 4: goal-mode validate ==="
"$PY" -c "
import json
from engine.goal_mode import run_goal_mode_cycle
r = run_goal_mode_cycle(batch_n=0, execute_paper=False, skip_batch=True, skip_monitor=True)
print(json.dumps({'ok': r.get('ok'), 'healthy': r.get('healthy'), 'fitness': (r.get('phases') or {}).get('backtest', {}).get('fitness')}, indent=2))
"

echo "=== Phase 5: web intel + social research (LLM) ==="
"$PY" -c "
from gateway.web_intel import build_web_intel
from engine.social_strategy_validation import run_social_strategy_validation
wi = build_web_intel('BTC/USDT')
soc = run_social_strategy_validation(use_llm=True)
print('web_intel_keys', list(wi.keys())[:8])
print('social_ok', soc.get('ok', soc.get('skipped')))
" || echo "[autonomous] web/social phase skipped: $?"

echo "=== Phase 6: resolve conflicts + ready draft PRs + executive consensus merge ==="
export EW_PR_AUTO_RESOLVE_CONFLICTS="${EW_PR_AUTO_RESOLVE_CONFLICTS:-1}"
if command -v gh >/dev/null 2>&1; then
  gh pr list --state open --json number,isDraft -q '.[] | select(.isDraft==true) | .number' 2>/dev/null | while read -r n; do
    [[ -n "$n" ]] && gh pr ready "$n" || true
  done
fi
export EW_PR_AUTO_APPROVE=1
export EW_PR_AUTO_MERGE=1
export EW_PR_MERGE_WITHOUT_PANEL=1
export EW_PR_LLM_ADVISORY="${EW_PR_LLM_ADVISORY:-1}"
export EW_LLM_BACKEND="${EW_LLM_BACKEND:-cursor}"
"$PY" ew_tool.py --pr-approve-all || echo "[autonomous] pr-approve-all note: $?" 

echo "=== Phase 7: persist daily summary ==="
"$PY" -c "
import json
from pathlib import Path
from engine.system_health import run_health_checks, save_health
from engine.autoresearch import latest_experiments_summary
from engine.improvement_cycle import improvement_report

health = run_health_checks()
save_health(health)
summary = {
  'finished_at': '${STAMP}',
  'log': '${LOG}',
  'healthy': health.get('healthy'),
  'autoresearch': latest_experiments_summary(),
  'improvement': improvement_report(),
}
pr_batch = Path('output/pr_reviews/batch_latest.json')
if pr_batch.exists():
  summary['pr_reviews'] = json.loads(pr_batch.read_text(encoding='utf-8'))
nightly = Path('output/nightly/run_summary.json')
if nightly.exists():
  summary['nightly'] = json.loads(nightly.read_text(encoding='utf-8'))
out = Path('output/autonomous/daily/latest_summary.json')
out.write_text(json.dumps(summary, indent=2, default=str), encoding='utf-8')
print(json.dumps(summary, indent=2, default=str))
"

echo "[autonomous] complete $(date -u +%Y-%m-%dT%H:%M:%SZ)"
