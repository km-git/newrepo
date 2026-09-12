# cost/audit

Workspace and OSS-tool inventory for the Cloud Cost & Configuration Review.

`cost audit inventory` writes `output/cost/cost-inventory.json` listing every
tool in this build (name, version, license, last-update, invocation mode).
Steampipe is recorded as a CLI subprocess (AGPL-3.0 — never imported).
Trivy is pinned at v0.71.2+ (never v0.69.4).

Primary tools: pip-audit locally; Mend Bolt for GitHub in CI.
