Standalone aggregate report. Reads `findings_dmarc`, writes
`reports/aggregate_YYYY-MM.html` with pass/fail by source and top sending IPs.
Plotly is preferred; an SVG fallback ships so Kibana is optional. DuckDB SQL
for the same view is in `dmarc.store.duckdb_view_sql`. Do not recommend
`p=reject` until pass rate is ≥ 99% for 30 days.
