# Cloud Cost & Configuration Review

Read-only cost and configuration reports for AWS, Azure, and GCP using free OSS tools at $0/month operator cost.

## Quick start

```bash
bash scripts/setup_environment.sh
pip install -e ".[dev]"
make cost-all
make cost-webui-static   # reports/cost_explorer.html
cost webui --host 0.0.0.0 --port 8766
```

Open **http://127.0.0.1:8766/cost** (Cloud Agent: use static HTML at `reports/cost_explorer.html`).

## Modules

1. `cost/audit` — OSS inventory (`cost audit inventory`)
2. `cost/aws_inventory` — AWS resources via Steampipe CLI subprocess
3. `cost/azure_inventory` — Azure ARM inventory
4. `cost/gcp_inventory` — GCP Cloud Asset inventory
5. `cost/cost_explorer` — DuckDB cost rollups (24-48h lag)
6. `cost/rightsizing` — heuristic recommendations (review before applying)
7. `cost/untagged` — tagging policy scan
8. `cost/config_drift` — Prowler snapshot diff
9. `cost/compliance_map` — framework reference mapping (not attestation)
10. `cost/report_writer` — Markdown + JSON report with AU disclaimer
11. `cost/loop` — Monday 09:00 AEST watcher + monthly rollup
12. `cost/multi_account` — c7n-org multi-account (dry-run)
13. `cost/webui` — browser dashboard

## Docker

```bash
docker compose -f docker-compose.cost.yml up -d postgres
```

## CI

`.github/workflows/cost-ci.yml` — pytest, Ruff, mypy, Trivy v0.71.2+ (never v0.69.x).
