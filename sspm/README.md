# SSPM-as-Report

Read-only SaaS configuration posture reports for Microsoft 365, Google Workspace,
GitHub, Slack, and Okta. Produces Configuration & Inventory Reports with OAuth
grant inventory, config drift detection, and control references.

## Quick start

```bash
pip install -e ".[dev]"
make sspm-all
sspm web serve --port 8766
```

Open http://127.0.0.1:8766/ for the Web UI dashboard.

## Modules

12 core modules + loop + web UI. JSON output by default; pass `--human` for tables.

## Reports

Every report ends with the AU liability disclaimer. This is **not** a security
assessment or attestation.
