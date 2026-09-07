# DSPM-like-Cyera — Build Prompt + Implementation

This directory contains the Cyera-equivalent DSPM build specification and the implemented package at `/workspace/dspm/`.

## Implementation status

| Stage | Status | Verification |
|-------|--------|--------------|
| 1 — Scaffold + audit + CI | Done | `make dspm-audit-inventory` |
| 2 — Discovery + classification | Done | `make dspm-classify` |
| 3 — Risk + exposure + access | Done | `make dspm-risk` |
| 4 — Remediation + loop + workflows | Done | `make dspm-all` |

## Quick start

```bash
cd dspm
pip install -e ".[dev]"
make test
make dspm-all
```

## Full build prompt

See `mavis-deep-research/20260907_dspm_cyera/final_turn_001.md` for the complete 12-module Cursor prompt, OSS tool mapping, forum-watcher sources, auto-PR/conflict/issue-fix patterns, and 5-stage improvement loop.

## Cursor rule

`.cursor/rules/dspm-cyera-build.mdc` — Apply Intelligently when working on DSPM modules.
