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

## Bootstrap (uv + Spec Kit + git hooks)

```bash
bash scripts/setup_spec_kit.sh       # uv, specify-cli from github/spec-kit
bash scripts/install_git_hooks.sh    # core.hooksPath → .githooks
bash scripts/setup_agent_harness.sh  # + optional ECC plugin instructions
```

## Typical feature flow

1. **Constitution** — `/speckit-constitution` (alias `/speckit.constitution`)
2. **Specify** — `/speckit-specify` (alias `/specify`) → `specs/…/spec.md`
3. **Plan** — `/speckit-plan` (alias `/plan`) → `plan.md`
4. **Tasks** — `/speckit-tasks` (alias `/tasks`) → `tasks.md`
5. **Implement** — `/speckit-implement` (alias `/spec-to-implementation`); hooks from `extensions.yml`
6. **Proof** — `/proof-first-trading` or `bash scripts/hooks/run_proof_gate.sh full`

## Hook layers

| Layer | Path |
|-------|------|
| Git | `.githooks/pre-commit` → fast proof on staged execution files |
| Kiro | `.kiro/hooks/*.json` |
| Spec Kit | `.specify/extensions.yml` |
| CI | `.github/workflows/proof-gate.yml` |

Skip: `EW_SKIP_PROOF_HOOKS=1`.

## Branch naming

Cloud agent branches: `cursor/<descriptive-name>-4874`. Feature spec ids: `001-feature-name`.

## GitHub CI

`.github/workflows/proof-gate.yml` runs fast pytest on paper/execution paths on PRs.
Full continuous proof runs on manual dispatch or nightly autonomous workflow.
