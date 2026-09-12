# Proof-first steering

Apply on every session that touches execution, paper simulation, or policy.

## Non-negotiables

- **Scoreboard**: `reports/PAPER_FORWARD.md`, `reports/CONTINUOUS_PROOF.md`, cumulative paper P&L.
- **Not scoreboard**: dense setup tables, SQS, LLM consensus, autodream narratives.
- **Verdicts**: report `PROOF_GO`, `PROOF_NO_GO`, or `PROOF_PENDING` only after running proof scripts.
- **LLM off for proof**: `EW_IMPROVEMENT_LLM=0` (set by `scripts/run_continuous_proof_loop.sh`).

## When to run proof

| Change area | Fast gate | Full proof |
|-------------|-----------|------------|
| `engine/paper_simulator.py` | `pytest tests/test_paper_simulator.py -q` | `bash scripts/run_continuous_proof_loop.sh` |
| `engine/paper_policy.py`, `engine/continuous_proof.py` | `pytest tests/test_paper_forward_tracker.py -q` | continuous proof loop |
| `engine/execution_gates.py`, geometry | `pytest tests/test_effectiveness_gates.py -q` | paper proof daily |
| Export-only / UI tables | pytest if tests exist | not required |

## Honesty rule

If proof is `PROOF_NO_GO` or P&L is negative, say so. Do not add rankers or filters to hide it.
Improve geometry, pair selection, or policy — not presentation.

## Spec Kit path

For new execution features use: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
`/speckit-implement`. Constitution: `.specify/memory/constitution.md`.
