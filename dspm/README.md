# DSPM — Cyera-like Data Security Posture Management

12-module OSS mosaic: Presidio, DuckDB, CloudQuery, Prowler, Trivy, Steampipe, Cloud Custodian, DataHub.

## Quick start

```bash
cd dspm
pip install -e ".[dev]"
make dspm-all
```

## Modules

| # | Module | OSS tool |
|---|--------|----------|
| 1 | audit | pip-audit + Mend Bolt |
| 2 | discovery | CloudQuery |
| 3 | classification | Presidio |
| 4 | risk | DuckDB |
| 5 | access | Steampipe (CLI) |
| 6 | exposure | Prowler |
| 7 | encryption_check | Trivy v0.70+ |
| 8 | shadow | CloudQuery + heuristics |
| 9 | custom_types | Presidio PatternRecognizer |
| 10 | compliance | Prowler + YAML controls |
| 11 | ai_security | DuckDB + regex (experimental) |
| 12 | remediation | Cloud Custodian |

Plus `loop/` for forum-watcher + monthly rollup.

## Cost

$0/month — GitHub Actions free tier, Gemini Flash free tier for LLM long-tail, all OSS tools.

## Honest gap

70-80% of Cyera value at 0% cost. Not a full Cyera replacement.
