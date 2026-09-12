# DSPM Platform — Enterprise Features + Web UI

## New in v0.2

- **Web UI** at `http://127.0.0.1:8766` — FastAPI dashboard with 9 panels
- **Catalog & Lineage** — Unity Catalog / OpenMetadata / Apache Polaris inspired
- **Governance** — Snowflake Horizon masking + row access policies
- **Observability** — Datadog-style metrics and alerting
- **SIEM** — Splunk-style event search and correlation
- **SQL Warehouse** — Databricks/Snowflake DuckDB workspace
- **GitHub Integrations** — Dependabot + secret scanning API

## Start

```bash
cd dspm && pip install -e ".[dev]" && make dspm-web
```
