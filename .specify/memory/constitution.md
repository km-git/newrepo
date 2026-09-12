# EW Tool Trading Constitution

## Core Principles

### I. Proof Before Product

No new rankers, scores, or execution paths ship without measurable proof. The scoreboard is
`reports/PAPER_FORWARD.md`, `reports/CONTINUOUS_PROOF.md`, and cumulative paper P&L — not dense
setup tables, SQS theater, or LLM narratives. Accuracy claims require pair×timeframe sample size
n≥5 or a completed paper-forward window.

### II. Valid Geometry (NON-NEGOTIABLE)

Every executable setup must pass deterministic geometry gates: stop-loss and take-profit ordering,
timeframe caps, ladder sequence, and direction/regime policy filters. WATCH is advisory only;
EXECUTE requires geometry + policy + paper gates. Elliott Wave and risk math stay deterministic and
test-covered.

### III. LLM-Free Proof Path

The canonical proof loop runs with `EW_IMPROVEMENT_LLM=0` and related AI flags off. LLM output is
advisory input only — never the acceptance criterion. Agents must run `scripts/run_continuous_proof_loop.sh`
or `scripts/run_paper_proof_daily.sh` after execution-path changes and report the verdict
(`PROOF_GO` / `PROOF_NO_GO` / `PROOF_PENDING`), not intermediate scores.

### IV. Spec-Driven Changes

Material execution or policy changes follow Spec Kit: constitution → specify → plan → tasks →
implement. Use `/speckit-*` Cursor skills. Feature artifacts live under `specs/<id>-<name>/`.
Steering in `.kiro/steering/` and this constitution override ad-hoc agent improvisation.

### V. Minimal, Honest Diffs

Prefer the smallest correct change. Do not add scoring layers, dashboards, or consensus theater
without a spec task and proof hook pass. Report honest outcomes including negative P&L and
`PROOF_NO_GO`; never substitute tables for edge.

## Execution Contract

- Paper default; live requires explicit confirmation and API credentials.
- Blocked timeframes and direction gates are policy, not suggestions.
- Paper simulator skips symbols without OHLC; junk pairs belong on learned blocklists.
- Continuous proof cycle: learn outcomes → refresh `engine/paper_policy.py` → paper-forward tick.

## Development Workflow

1. Read `.kiro/steering/` and this constitution before execution changes.
2. For new behavior: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.
3. Hooks (`.kiro/hooks/`, `.specify/extensions.yml`) run pytest subsets and proof scripts.
4. PRs touching `engine/paper_*`, `engine/execution_*`, or proof scripts must show hook/CI results.

## Governance

This constitution supersedes informal agent habits. Amendments require updating
`.specify/memory/constitution.md`, syncing `.kiro/steering/`, and a PR description that states
what proof gate changed. All reviews verify geometry tests and proof verdict, not narrative quality.

**Version**: 1.0.0 | **Ratified**: 2026-09-11 | **Last Amended**: 2026-09-11
