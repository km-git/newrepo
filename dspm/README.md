# DSPM Platform — Data Security Posture Management

Cyera-like DSPM built from OSS components, now with **enterprise platform modules** and a **web UI**.

## Quick start

```bash
cd dspm
pip install -e ".[dev]"
make test
make dspm-all
make dspm-web    # → http://127.0.0.1:8766
```

## Web UI

```bash
python -m dspm web serve --port 8766
# or: dspm-web serve
```

Dashboard pages: Findings, Risk, Exposure, Catalog & Lineage, Governance, SIEM, SQL Warehouse, Remediation.

API docs: http://127.0.0.1:8766/api/docs

## Platform modules (enterprise-inspired)

| Module | Inspired by | Features |
|--------|-------------|----------|
| `catalog` | Databricks Unity Catalog, OpenMetadata, Apache Polaris | Asset registry, lineage graph, tag taxonomy |
| `governance` | Snowflake Horizon | Masking policies, row access policies, role-based mask preview |
| `observability` | Datadog | Metrics, alert rules, health dashboard |
| `siem` | Splunk | Event ingest, regex search, attack-chain correlation |
| `warehouse` | Databricks/Snowflake | DuckDB SQL workspace, query audit history |
| `integrations` | GitHub Security | Dependabot alerts, secret scanning, org repo inventory |
| `web` | — | FastAPI dashboard + REST API |

## Core DSPM modules (12)

audit, discovery, classification, risk, access, exposure, encryption_check, shadow, custom_types, compliance, ai_security, remediation, loop

## Cost

$0/month — GitHub Actions, Gemini Flash free tier, OSS tools, SQLite persistence.

## Honest gap

70-80% of Cyera + partial enterprise platform features at 0% cost. Not a full Databricks/Snowflake/Datadog/Splunk replacement.
