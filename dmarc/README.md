# DMARC Deliverability & Brand-Protection Monitor

Read-only Email Deliverability & Brand-Protection Review for AU SMB customers — DNS (SPF/DKIM/DMARC), aggregate RUA ingest, Plotly reports, inbox placement heuristics, and a web dashboard.

## Quick start

```bash
cd dmarc
make install
make dmarc-all DOMAIN=example.com.au
make dmarc-web    # http://127.0.0.1:8767
```

Integrated into the EW monitor hub:

```bash
python3 ew_tool.py --monitor   # open /dmarc on port 8765
```

## Modules

| Module | CLI | Purpose |
|--------|-----|---------|
| audit | `dmarc audit inventory` | OSS tool inventory + pip-audit |
| dns_check | `dmarc dns check --domain` | A/AAAA/MX/TXT/DMARC/DKIM/MTA-STS/TLS-RPT/BIMI |
| spf_parser | `dmarc spf parse --domain` | SPF lookup count + warnings |
| dkim_check | `dmarc dkim check --domain` | DKIM key length checks |
| dmarc_ingest | `dmarc ingest pull --demo` | RUA ingest (IMAP or samples) |
| aggregate_report | `dmarc aggregate report` | Plotly HTML dashboard |
| forensic_report | `dmarc forensic list` | RUF parser + Presidio scrub |
| inbox_placement | `dmarc inbox test` | Seed placement heuristics |
| report_writer | `dmarc report generate` | Markdown + JSON + disclaimer |

## Environment

- `DMARC_IMAP_PASS` — IMAP password (never commit)
- `DMARC_DB_PATH` — DuckDB path (default `output/dmarc.duckdb`)
- `GEMINI_API_KEY` — optional forum-watcher classifier

## Honest gaps

- Inbox placement is heuristic; run weekly and track trends.
- RUF/forensic reports are rarely sent by receivers.
- Optional Elasticsearch stack: `docker compose --profile elastic up`

Every report ends with the AU liability disclaimer in `disclaimers/disclaimer_au.txt`.
