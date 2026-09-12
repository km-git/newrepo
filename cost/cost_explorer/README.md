# cost/cost_explorer

Daily and monthly cost rollup per service, region, tag, and account.

CLI: `cost cost-explorer --provider aws --since 30d`

Uses the customer's AWS Cost Explorer / Azure Cost Management / GCP Cloud
Billing APIs (free with their account). DuckDB (or SQLite fallback) for
cross-provider SQL. Cost data has a 24–48h lag — this tool does not promise
real-time figures.
