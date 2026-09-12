# Tasks: Proof-governed execution methodology

**Input**: [plan.md](./plan.md), [spec.md](./spec.md)

## Phase 1 — Foundation

- [x] T001 Customize `.specify/memory/constitution.md` with proof-first trading principles
- [x] T002 Create `.kiro/steering/proof-first.md`, `execution-contract.md`, `spec-workflow.md`
- [x] T003 Add `scripts/hooks/run_proof_gate.sh` (fast pytest + optional full proof)

## Phase 2 — Hooks & skills

- [x] T004 Add `.kiro/hooks/pytest-paper-on-save.json`
- [x] T005 Add `.kiro/hooks/proof-loop-on-execution.json` and `session-start-steering.json`
- [x] T006 Add `.cursor/skills/proof-first-trading/SKILL.md`
- [x] T007 Add `.specify/extensions.yml` with before/after implement hooks
- [x] T008 Set `.specify/feature.json` → `specs/001-proof-governed-execution`

## Phase 3 — CI & docs

- [x] T009 Add `.github/workflows/proof-gate.yml`
- [x] T010 Update `AGENTS.md` with Spec Kit + Kiro + proof hook section
- [x] T011 Update `.gitignore` — commit skills/rules, ignore credentials

## Phase 4 — Validation

- [x] T012 `chmod +x scripts/hooks/run_proof_gate.sh`
- [ ] T013 Run `bash scripts/hooks/run_proof_gate.sh fast` in CI (proof-gate workflow)
- [ ] T014 Optional: manual `run_proof_gate.sh full` on merge to validate ledger
