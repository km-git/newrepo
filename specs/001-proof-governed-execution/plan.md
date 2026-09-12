# Implementation Plan: Proof-governed execution methodology

**Branch**: `cursor/kiro-spec-kit-proof-4874` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

## Summary

Install GitHub Spec Kit with Cursor integration, add Kiro-compatible steering and hooks that call
existing LLM-free proof scripts, and register Spec Kit `extensions.yml` hooks so implement phases
run proof gates automatically.

## Technical Context

**Language/Version**: Python 3.12, Bash  
**Primary Dependencies**: `specify-cli` 1.0.6, `ew_tool.py`, pytest  
**Storage**: `reports/` (gitignored artifacts), `specs/` (committed)  
**Testing**: `tests/test_paper_simulator.py`, `tests/test_paper_forward_tracker.py`, `tests/test_execution_gates.py`  
**Target Platform**: GitHub + Cursor Cloud Agent  
**Constraints**: `EW_IMPROVEMENT_LLM=0` for proof; no new rankers without spec + proof

## Project Structure

```text
.specify/
  memory/constitution.md
  extensions.yml
  feature.json
.kiro/
  steering/*.md
  hooks/*.json
.cursor/skills/
  speckit-*/
  proof-first-trading/
scripts/hooks/
  run_proof_gate.sh
specs/001-proof-governed-execution/
  spec.md, plan.md, tasks.md
.github/workflows/
  proof-gate.yml
```

## Phase 0 — Research

- Kiro hooks v1 schema: `.kiro/hooks/*.json`, triggers `PostFileSave`, `SessionStart`
- Spec Kit hooks: `.specify/extensions.yml` `before_implement` / `after_implement`
- Existing proof entrypoints: `run_continuous_proof_loop.sh`, `run_paper_proof_daily.sh`

## Phase 1 — Foundation

1. Customize constitution (proof-first trading contract).
2. Add steering files mirroring Kiro `.kiro/steering/`.
3. Shared `scripts/hooks/run_proof_gate.sh` for fast/full modes.

## Phase 2 — Hooks & skills

1. Kiro JSON hooks for pytest on paper modules and full proof on script changes.
2. `proof-first-trading` Cursor skill.
3. `extensions.yml` for speckit-implement integration.

## Phase 3 — CI & docs

1. `proof-gate.yml` workflow on PR path filters.
2. Extend `AGENTS.md` with methodology section.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Dual hook systems (Kiro + Spec Kit) | Cursor uses skills/extensions; Kiro IDE uses `.kiro/hooks` | Single system would break Kiro portability goal |
