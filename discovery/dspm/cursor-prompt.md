# DSPM-like-Cyera — Cursor build prompt (executable sibling)

Paste-oriented prompt lives in the operator notes under `mavis-deep-research/20260907_dspm_cyera_cursor_prompt/`. This tree is the implementation: `dspm/` with 12 modules, `dspm/loop/` for the 5-stage watcher, and `.github/workflows/dspm-*.yml` for CI / auto-approve / rebase / monthly / keepalive / issue-fix.

## Modules

1. `dspm/audit` — inventory of OSS tools + licenses
2. `dspm/discovery` — CloudQuery CLI + directory walk
3. `dspm/classification` — Presidio-compatible recognizers (stdlib; optional Presidio)
4. `dspm/risk` — weighted SQL formula (DuckDB when installed)
5. `dspm/access` — Steampipe subprocess
6. `dspm/exposure` — Prowler JSON
7. `dspm/encryption_check` — Trivy 0.71.2+
8. `dspm/shadow` — heuristic unmanaged stores
9. `dspm/custom_types` — AU TFN / ABN / NHS YAML registry
10. `dspm/compliance` — GDPR/HIPAA/PCI/SOC2 YAML map
11. `dspm/ai_security` — experimental prompt-log scanner
12. `dspm/remediation` — four Cloud Custodian policies (manual merge)

## Gates

- Trivy never 0.69.4 (CVE-2026-33634)
- Steampipe never imported
- Presidio from data-privacy-stack
- SHA-pinned Actions
- $0/month
