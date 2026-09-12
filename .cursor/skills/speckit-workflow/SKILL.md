---
name: "speckit-workflow"
description: "End-to-end Spec Kit flow with proof hooks — constitution through implementation."
compatibility: "Requires .specify/, .kiro/steering/, scripts/hooks/run_proof_gate.sh"
metadata:
  author: "ew-tool"
---

## Command map (Cursor slash names)

| Step | Cursor skill | Alternate names |
|------|--------------|-----------------|
| 1 | `/speckit-constitution` | `/speckit.constitution` |
| 2 | `/speckit-specify` | `/specify` |
| 3 | `/speckit-plan` | `/plan` |
| 4 | `/speckit-tasks` | `/tasks` |
| 5 | `/speckit-implement` | `/spec-to-implementation` |
| 6 | `/proof-first-trading` | proof gate after execution changes |

## Full flow

1. Read `.specify/memory/constitution.md` and `.kiro/steering/proof-first.md`.
2. `/speckit-constitution` — only when governance changes.
3. `/speckit-specify` — user story → `specs/<id>-<name>/spec.md`.
4. `/speckit-plan` → `plan.md`.
5. `/speckit-tasks` → `tasks.md`.
6. `/speckit-implement` — runs `extensions.yml` hooks (fast pytest before, optional full proof after).
7. `/proof-first-trading` — report `PROOF_GO` / `PROOF_NO_GO` / `PROOF_PENDING` only.

## Bootstrap (one-time)

```bash
bash scripts/setup_spec_kit.sh      # uv + specify-cli from github/spec-kit
bash scripts/install_git_hooks.sh   # git config core.hooksPath .githooks
bash scripts/setup_agent_harness.sh # optional ECC plugin instructions + hooks
```

## Hooks stack

| Layer | Trigger | Action |
|-------|---------|--------|
| Git `.githooks/pre-commit` | staged paper/execution | `run_proof_gate.sh fast` |
| Kiro `.kiro/hooks/*.json` | PostFileSave | pytest or full proof |
| Spec Kit `.specify/extensions.yml` | before/after implement | proof-first-trading |
| CI `proof-gate.yml` | PR path filter | fast pytest |

Skip hooks once: `EW_SKIP_PROOF_HOOKS=1`.
