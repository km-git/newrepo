# DSPM-like-Cyera — Cursor build prompt + continuous-improvement plumbing

Implemented in-repo as the `dspm/` sibling package (12 modules + `dspm/loop/`). Full operator prompt is `discovery/dspm/cursor-prompt.md`. Framing from the 2026-09-07 research turn:

## Mapping (Cyera → OSS)

| # | Capability | Primary OSS | Honest gap |
|---|----------------|----------|------------|
| 1 | Agentless inventory | CloudQuery | Classification is a later stage |
| 2 | AI-native classification | Presidio (`data-privacy-stack/presidio`) | ~75-85% vs claimed >95% |
| 3 | Risk scoring | DuckDB SQL / identical Python formula | Not proprietary ML |
| 4 | Access governance | Steampipe CLI (AGPL-3.0, subprocess only) | Partial identity unification |
| 5 | Public exposure | Prowler | Narrower than commercial DSPM |
| 6 | Encryption | Trivy **0.71.2** (never 0.69.4 / CVE-2026-33634) | Metadata-based at-rest |
| 7 | Shadow data | CloudQuery heuristics | Not ML |
| 8 | Custom types | YAML PatternRecognizer | Long tail needs LLM |
| 9 | Compliance | Prowler + YAML maps | Hand-maintained |
| 10 | AI workload | Experimental prompt-log scanner | Not a product |
| 11 | Remediation | Cloud Custodian (4 policies, never auto-merged) | vs 30+ vendor actions |
| 12 | Re-discovery | GitHub Actions cron + keepalive timestamp | 60-day pause mitigated in-repo |

## Cost

$0/month. Gemini Flash free tier for 95% of LLM. No Sonnet/Opus in this build.

## Loops

Forum watcher (`dspm/loop/watch.py`) + `scripts/watch.py` wrapper. Auto-approve bots only. Rebase Dependabot. Issue auto-fix for `good first issue` mechanical tickets. Keepalive does **not** use `gautamkrishnar/keepalive-workflow` (GitHub-disabled).
