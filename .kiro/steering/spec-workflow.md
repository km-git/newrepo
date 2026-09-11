# Spec Kit + Kiro workflow steering

This repo uses a Kiro-like loop on GitHub: **Spec Kit** for structured specs, **Cursor skills**
for commands, **proof scripts** as hooks.

## Directory map

| Path | Role |
|------|------|
| `.specify/memory/constitution.md` | Governance — proof-first trading rules |
| `.specify/extensions.yml` | Spec Kit implement hooks → proof scripts |
| `.cursor/skills/speckit-*` | Slash commands: specify, plan, tasks, implement |
| `.cursor/skills/proof-first-trading` | Proof gate skill for agents |
| `.kiro/steering/` | Always-on steering (this folder) |
| `.kiro/hooks/` | Post-save / session hooks → pytest & proof |
| `specs/<id>-<name>/` | Feature spec, plan, tasks |
| `scripts/hooks/` | Shared shell entrypoints for hooks & CI |

## Typical feature flow

1. **Constitution** — `/speckit-constitution` if governance changes.
2. **Specify** — `/speckit-specify` with user story; creates `specs/…/spec.md`.
3. **Plan** — `/speckit-plan` → `plan.md`.
4. **Tasks** — `/speckit-tasks` → `tasks.md`.
5. **Implement** — `/speckit-implement` (runs proof hooks from `extensions.yml`).
6. **Proof** — `bash scripts/run_continuous_proof_loop.sh`; read verdict in reports.

## Branch naming

Cloud agent branches: `cursor/<descriptive-name>-4874`. Feature spec ids: `001-feature-name`.

## GitHub CI

`.github/workflows/proof-gate.yml` runs fast pytest on paper/execution paths on PRs.
Full continuous proof runs on manual dispatch or nightly autonomous workflow.
