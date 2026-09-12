# SSPM-as-report

Read-only **Configuration & Inventory Report** for Microsoft 365, Google Workspace, GitHub, Slack, and Okta. Mondoo cnspec is the scan backbone; DuckDB/SQLite diffs settings against shipped baselines; Jinja (or stdlib fallback) writes Markdown + JSON + HTML with an AU liability disclaimer.

This is not AppOmni. Honest gap is roughly 60–75% of commercial SSPM (no identity graph, no inline CASB, no live token analytics).

## Quick start

```bash
python3 -m sspm audit inventory
python3 -m sspm discovery m365
python3 -m sspm report generate --tenant m365 --output output/sspm/report.md
make sspm-all
python3 -m sspm web --static   # reports/sspm_explorer.html
python3 ew_tool.py --sspm-ui --static
```

Live APIs require customer-authorised credentials and `SSPM_LIVE=1`. Fixtures under `sspm/fixtures/` are the default path.

## 12 modules

audit · m365_discovery · google_workspace_discovery · github_discovery · slack_discovery · okta_discovery · oauth_grants · config_drift · compliance_map · report_writer · multi_tenant · disclaimers

`sspm/loop/` extends the existing forum-watcher (Monday 09:00 AEST). Do not duplicate it.
