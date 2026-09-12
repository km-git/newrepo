# Feature Specification: Proof-governed execution changes

**Feature Branch**: `cursor/kiro-spec-kit-proof-4874`

**Created**: 2026-09-11

**Status**: Active (methodology baseline)

**Input**: Kiro-like working methodology on GitHub with Spec Kit + Cursor skills + proof scripts as hooks.

## User Scenarios & Testing

### User Story 1 - Spec-driven execution change (Priority: P1)

As a maintainer, I define execution or paper-sim changes in a spec before coding, so agents do not ship unscored table theater.

**Why this priority**: Prevents repeat of SQS/ranker layers without edge proof.

**Independent Test**: Create `specs/002-*/spec.md` via `/speckit-specify`; implement via `/speckit-implement`; hooks run pytest + proof loop.

**Acceptance Scenarios**:

1. **Given** a change to `engine/paper_simulator.py`, **When** the agent saves the file, **Then** Kiro hook runs `run_proof_gate.sh fast` and pytest passes.
2. **Given** `/speckit-implement` on an execution feature, **When** implementation completes, **Then** `extensions.yml` triggers proof-first-trading and reports verdict from `reports/CONTINUOUS_PROOF.md`.

---

### User Story 2 - Honest scoreboard (Priority: P1)

As a trader, I see only paper-forward P&L and PROOF verdict as success criteria.

**Why this priority**: Architecture exists; profitability does not yet (`PROOF_NO_GO` is valid).

**Independent Test**: Run `bash scripts/run_continuous_proof_loop.sh`; read `reports/CONTINUOUS_PROOF.md`.

**Acceptance Scenarios**:

1. **Given** LLM flags off, **When** continuous proof runs, **Then** output includes verdict line and cumulative P&L without LLM narrative.
2. **Given** negative P&L, **When** agent summarizes, **Then** it states `PROOF_NO_GO` without adding new rankers.

---

### User Story 3 - Steering at session start (Priority: P2)

As an agent, I load proof-first rules automatically like Kiro steering files.

**Independent Test**: `.kiro/hooks/session-start-steering.json` exists and references `.kiro/steering/`.

**Acceptance Scenarios**:

1. **Given** a new session, **When** SessionStart hook fires, **Then** agent is prompted to read constitution and steering.

---

### Edge Cases

- Missing `.venv`: `run_proof_gate.sh` exits non-zero with setup instructions.
- No OHLC for symbol: paper sim skips; proof loop still completes.
- `PROOF_PENDING`: report insufficient ledger days; do not claim GO.

## Requirements

### Functional Requirements

- **FR-001**: Constitution at `.specify/memory/constitution.md` MUST encode proof-before-product rules.
- **FR-002**: `.kiro/hooks/` MUST wire PostFileSave matchers to `scripts/hooks/run_proof_gate.sh`.
- **FR-003**: `.specify/extensions.yml` MUST register before/after implement proof hooks.
- **FR-004**: `.cursor/skills/proof-first-trading` MUST document fast vs full proof invocation.
- **FR-005**: CI workflow MUST run fast proof gate on PRs touching paper/execution paths.

### Key Entities

- **Verdict**: `PROOF_GO`, `PROOF_NO_GO`, `PROOF_PENDING` from continuous proof report.
- **Scoreboard**: `reports/PAPER_FORWARD.md`, `reports/CONTINUOUS_PROOF.md`.
- **Steering**: `.kiro/steering/*.md` — always-on agent context.

## Success Criteria

- **SC-001**: Agent can run `/speckit-specify` through `/speckit-implement` with proof hooks documented.
- **SC-002**: Saving `engine/paper_simulator.py` triggers fast pytest via hook definition (Kiro-compatible JSON).
- **SC-003**: PR CI runs `run_proof_gate.sh fast` when execution paths change.
