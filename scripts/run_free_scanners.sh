#!/usr/bin/env bash
# Local stand-in for lint-security.yml + bugbot-free.yml.
# No paid SaaS (CodeRabbit/Sourcery/Mend/Socket/Aikido/Sentry).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
else
  PY="python3"
fi

need() {
  local name="$1"
  if [[ -x "${ROOT}/.venv/bin/${name}" ]]; then
    printf '%s\n' "${ROOT}/.venv/bin/${name}"
    return 0
  fi
  if command -v "${name}" >/dev/null 2>&1; then
    command -v "${name}"
    return 0
  fi
  return 1
}

ensure() {
  local name="$1"
  local spec="$2"
  if need "${name}" >/dev/null; then
    need "${name}"
    return 0
  fi
  echo "Installing ${spec} into the active Python..." >&2
  "${PY}" -m pip install -q "${spec}"
  need "${name}"
}

RUFF_PATHS=(
  tape_to_cloud/
  dspm/
  engine/monetization_strategy.py
  engine/tape_to_cloud_hub.py
  engine/tape_to_cloud_report_html.py
  engine/tape_to_cloud_reports.py
  tests/test_monetization_strategy.py
  tests/test_tape_to_cloud_monetize.py
  tests/test_tape_to_cloud_hub.py
  tests/test_tape_to_cloud_layers.py
  tests/test_tape_to_cloud_reports.py
  tests/test_tape_to_cloud_pipeline.py
  tests/test_bugbot_replacement.py
  tests/test_dspm_architecture.py
  tests/test_dspm_core.py
  tests/test_dspm_loop.py
  tests/test_dspm_improve.py
)

SEMGREP_PATHS=(
  tape_to_cloud/
  dspm/
  engine/tape_to_cloud_hub.py
  engine/tape_to_cloud_reports.py
  ew_tool.py
)

echo "== ruff =="
RUFF="$(ensure ruff 'ruff>=0.9.0')"
"${RUFF}" check --config ruff.toml "${RUFF_PATHS[@]}"
"${RUFF}" format --check "${RUFF_PATHS[@]}"

echo "== pip-audit =="
PIP_AUDIT="$(ensure pip-audit 'pip-audit')"
# PYSEC-2026-2447: diskcache pickle RCE if an attacker can write the cache dir.
"${PIP_AUDIT}" -r requirements.txt --desc on --ignore-vuln PYSEC-2026-2447

echo "== zizmor (high) =="
ZIZMOR="$(ensure zizmor 'zizmor>=1.30.0')"
"${ZIZMOR}" --config zizmor.yml --persona=regular --min-severity high .github/workflows

if command -v actionlint >/dev/null 2>&1; then
  echo "== actionlint =="
  actionlint -shellcheck= -color
else
  echo "== actionlint == skipped (binary not on PATH)"
fi

echo "== semgrep CE =="
SEMGREP="$(ensure semgrep 'semgrep>=1.100.0')"
"${SEMGREP}" scan \
  --config p/python \
  --config p/security-audit \
  --metrics off \
  "${SEMGREP_PATHS[@]}"

echo "All free scanners passed."
