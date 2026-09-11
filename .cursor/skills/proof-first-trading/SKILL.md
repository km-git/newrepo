---
name: "proof-first-trading"
description: "Run LLM-free proof gates after execution or paper-sim changes; report PROOF_GO/NO_GO/PENDING only."
compatibility: "Requires ew_tool.py, scripts/run_continuous_proof_loop.sh, .venv"
metadata:
  author: "ew-tool"
  source: ".kiro/steering/proof-first.md"
---

## When to use

Invoke after editing any of:

- `engine/paper_simulator.py`, `engine/paper_policy.py`, `engine/continuous_proof.py`
- `engine/paper_forward_tracker.py`, `engine/execution_gates.py`
- `scripts/run_continuous_proof_loop.sh`, `scripts/run_paper_proof_daily.sh`
- Spec Kit implement phase for execution features (`specs/*` touching paper or execute)

Do **not** use for export-only UI or documentation-only changes.

## User Input

```text
$ARGUMENTS
```

If `$ARGUMENTS` contains `fast`, run pytest only. If `full` or empty on execution changes, run continuous proof.

## Steps

1. **Read steering** — `.kiro/steering/proof-first.md` and `.specify/memory/constitution.md`.

2. **Fast gate** (always):
   ```bash
   cd "$(git rev-parse --show-toplevel)"
   export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
   .venv/bin/python -m pytest tests/test_paper_simulator.py tests/test_paper_forward_tracker.py tests/test_paper_policy.py tests/test_effectiveness_gates.py -q --tb=short
   ```
   Stop and fix failures before continuing.

3. **Full proof** (when `$ARGUMENTS` is not `fast`):
   ```bash
   bash scripts/run_continuous_proof_loop.sh
   ```

4. **Report** — Read and summarize only:
   - `reports/CONTINUOUS_PROOF.md` (verdict line)
   - `reports/PAPER_FORWARD.md` if present (cumulative P&L, days filled)
   - Do not paste dense setup tables or SQS scores.

5. **Verdict format** (required):
   ```
   Proof verdict: PROOF_GO | PROOF_NO_GO | PROOF_PENDING
   Cumulative paper P&L: <value or unknown>
   Blockers: <geometry | pair selection | insufficient days | none>
   ```

## Rules

- Set `EW_IMPROVEMENT_LLM=0` for proof runs (scripts already do).
- Never claim edge from tables; only from proof artifacts above.
- If `PROOF_NO_GO`, suggest geometry/policy fixes — not new rankers.
