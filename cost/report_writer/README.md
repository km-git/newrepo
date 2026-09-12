# cost/report_writer

Produces `report.md` and `report.json` for a Cloud Cost & Configuration
Review. Sections: cost summary, top drivers, rightsizing, untagged inventory,
drift, framework references, liability disclaimer.

CLI: `cost report generate --provider aws --since 30d --output report.md`

Jinja2 (or stdlib fallback) plus `disclaimers/disclaimer_au.txt`.
