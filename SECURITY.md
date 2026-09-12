# Security policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/km-git/newrepo/security/advisories/new).
Do not open a public issue that includes secrets, credentials, exploit PoCs, or customer data.

We aim to acknowledge reports within seven days.

## Scope

This repository is a Python CLI (`ew_tool.py`) plus sibling tools (tape-to-cloud, DSPM, DMARC, cost, SSPM). Supply-chain, secret, and static scanning run in GitHub Actions:

- `.github/workflows/lint-security.yml` — Ruff, pip-audit, actionlint, gitleaks, OSV, zizmor, TruffleHog
- `.github/workflows/bugbot-free.yml` — CodeQL + Semgrep CE + reviewdog
- `.github/workflows/scorecard.yml` — OpenSSF Scorecard
- `.github/workflows/dependency-review.yml` — PR dependency diff

Local equivalent: `make scan` or `bash scripts/run_free_scanners.sh`.

Do not commit API keys, account identifiers, or raw customer payloads.
