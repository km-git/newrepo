# Cloud Cost & Configuration Review

Read-only cost and configuration reporting for AWS, Azure, and GCP. Not a
security assessment. CLI + JSON + stdlib Web UI.

```bash
.venv/bin/python -m cost scan-all --sandbox
.venv/bin/python -m cost ui --static          # reports/cost_explorer.html
.venv/bin/python ew_tool.py --cost-ui         # http://127.0.0.1:8765/cost
make cost-all
```

Ten modules under `cost/` plus `loop/` (forum-watcher payload) and
`multi_account/` (c7n-org dry-run). Steampipe is a CLI subprocess only
(AGPL-3.0). Trivy is pinned to v0.71.2+. Cloud Custodian policies in
`cost/remediation/` are dry-run and require manual review to merge.
