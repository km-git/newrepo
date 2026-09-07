You are extending an existing 16-module tape-to-cloud migration tool and its 12-module DSPM sibling (the prior 11 turns of build context) with a new sibling project: a **DMARC + Email Deliverability** tool — an MSP-ready authentication and inbox-placement report for customer domains. Build it entirely from open-source components, with continuous forum-driven feature discovery, automatic PR approval for bot PRs, automatic conflict resolution, automatic issue fixing, and the 5-stage improvement loop. Primary engines: **parsedmarc** (aggregate / failure / TLS-RPT) and **dnspython** (SPF, DKIM, DMARC, BIMI, MTA-STS, TLS-RPT, MX). The 95/5 model discipline routes scaffolding to Grok Code Fast / Composer 2.5 Standard / `gemini-2.5-flash` (free tier) and reserves Claude Sonnet 5 / Opus 5 / Fable 5.1 for named hard triggers only. Total monthly cost: $0. This is a **draft DNS/report pack**, not an auto-publisher of DNS records.

## 0. Read first

Before writing any code, read every file in `/workspace/mavis-deep-research/`. Then read, if present:

- `discovery/tape-to-cloud/cursor-prompt.md`
- `discovery/tape-to-cloud/continuous-improvement-loop-prompt.md`
- `discovery/dspm/cursor-prompt.md` and `dspm/README.md`
- `4-safe-builds-prompts/01-SSPM-CURSOR-PROMPT.md` (posture sibling; this product is **email auth**)
- `forum-watcher/sources.yaml` and `forum-watcher/scripts/watch.py`
- `.cursor/rules/tape-to-cloud-build.mdc`

Do not re-implement tape-to-cloud, DSPM, SSPM, costreview, licensespend, the forum-watcher, or the Bugbot replacement. Do not break `peter-evans/create-pull-request@v8` or `hmarr/auto-approve-action@v4`. Do **not** use `gautamkrishnar/keepalive-workflow`; keep cron alive with `dmarcdeliv/state/keepalive.txt`. SHA-pin every GitHub Action. Cron: Monday 09:00 AEST, `timezone: Australia/Sydney`.

Operator: 1-person AU MSP. Customers: AU SMBs with Microsoft 365 or Google Workspace mail, often `p=none` forever. Output is a **draft for human DNS apply**. Never call a DNS provider API (Cloudflare, GoDaddy, Route53) unless `--apply` **and** `DMARCDELIV_APPLY=1` **and** the record change is in `allow-dns.txt`.

**PII:** DMARC aggregate (RUA) is counts by source IP / org. Failure/RUF reports can contain message samples — **drop or redact RUF bodies**. Store source IP, header-from, disposition, SPF/DKIM results, counts. Do not store subject lines, recipients, or MIME. TLS-RPT is policy/failure counts — keep it.

parsedmarc can ingest IMAP/Graph/Gmail. Prefer **fixture XML/JSON** in pytest. Live inbox ingest is optional extra and must use a dedicated reporting mailbox, not a user's inbox.

## 1. The 9-module architecture

Create a Python package `dmarcdeliv/` with exactly these 9 modules. Each: `cli.py` (Typer), `service.py`, `models.py` (Pydantic v2), `tests/`, `README.md` (≤ 200 words). JSON default; `--human` for a table. Fixture-first.

1. `dmarcdeliv/audit/` — tool + license inventory. CLI: `dmarcdeliv audit inventory`.
2. `dmarcdeliv/dns/` — live or fixture DNS for a domain: MX, TXT SPF, `_dmarc`, `selector._domainkey`, `_bimi`, `_mta-sts`, `_smtp._tls`, HTTPS `https://mta-sts.<domain>/.well-known/mta-sts.txt`. CLI: `dmarcdeliv dns check example.com --fixture examples/dns/example.com.json`. **Primary: dnspython. Fixture mode uses recorded answers so CI is offline.**
3. `dmarcdeliv/ingest/` — parse RUA XML (gzip/zip), TLS-RPT JSON, optional RUF with body stripped. Wrap `parsedmarc` (`parse_report_file` / CLI). CLI: `dmarcdeliv ingest rua examples/rua/` and `dmarcdeliv ingest tlsrpt examples/tlsrpt/`. **Primary: parsedmarc. Store to DuckDB/Postgres `agg_records`. Honest gap: no commercial threat intel feed.**
4. `dmarcdeliv/alignment/` — SPF/DKIM alignment rates, disposition (`none|quarantine|reject`), pct. DuckDB rollups by day / source org. CLI: `dmarcdeliv alignment summary --domain example.com --since 30d`.
5. `dmarcdeliv/sources/` — sending sources inventory: IP → org → volume → pass/fail. Flag unknown sources vs `dmarcdeliv/sources/allowlist.yaml` (ESP names: Microsoft, Google, SendGrid, Mailchimp, etc.). CLI: `dmarcdeliv sources list --domain example.com`.
6. `dmarcdeliv/threats/` — spoof/fail clusters: high-volume fail from non-allowlisted orgs, new sources this week. CLI: `dmarcdeliv threats scan`. **Draft only. Not a SOC product. No malware detonation.**
7. `dmarcdeliv/tls/` — MTA-STS mode (`testing|enforce`), MX coverage vs policy, TLS-RPT failure reasons. CLI: `dmarcdeliv tls status --domain example.com`.
8. `dmarcdeliv/blacklist/` — DNSBL lookups (Zen/Spamhaus-like, Barracuda, etc.) for **customer outbound MX / dedicated send IPs** listed in YAML — not for every RUA IP (that is noisy and can violate DNSBL ToS). CLI: `dmarcdeliv blacklist check --fixture examples/dnsbl/`. **Honest gap: many DNSBLs rate-limit; fixtures + optional live with caching.**
9. `dmarcdeliv/report/` — **the product**. HTML + Markdown + JSON: auth scorecard, alignment trend, source table, recommended DNS **drafts** (SPF flattening warning, DMARC p=none→quarantine ladder, BIMI prerequisites, MTA-STS testing), SHA-256 watermark. CLI: `dmarcdeliv report build --domain example.com --out reports/`. Static HTML. Recommend module is part of this report (do not split an extra package): `dmarcdeliv report drafts` prints TXT records for human paste.

A 10th module `dmarcdeliv/loop/` reuses the forum-watcher.

## 2. The `pyproject.toml`

```toml
[project]
name = "dmarcdeliv"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "parsedmarc>=8.0.0",
  "dnspython>=2.7.0",
  "duckdb>=1.2.0",
  "pyarrow>=17.0.0",
  "httpx>=0.27.0",
  "pydantic>=2.9.0",
  "typer>=0.15.0",
  "pyyaml>=6.0.2",
  "feedparser>=6.0.11",
  "rich>=13.9.0",
  "jinja2>=3.1.4",
  "lxml>=5.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-cov>=6.0.0",
  "ruff>=0.9.0",
  "mypy>=1.14.0",
  "pip-audit>=2.7.0",
]
imap = ["mailsuite"]
graph = ["msgraph-sdk", "azure-identity"]

[project.scripts]
dmarcdeliv = "dmarcdeliv.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

parsedmarc already depends on dnspython. Pin both explicitly. Elasticsearch/Kibana are **optional** parsedmarc backends — default store is DuckDB/Parquet so `$0` and no JVM. If you add OpenSearch later, keep it a profile, not the default.

## 3. The `docker-compose.yml` for local dev

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: dmarcdeliv
      POSTGRES_PASSWORD: dmarcdeliv
      POSTGRES_DB: dmarcdeliv
    ports: ["5436:5432"]
```

Default `make dmarcdeliv-all` must work with DuckDB only (no Compose required). No MinIO. No Elasticsearch requirement.

## 4. The GitHub Actions workflows

Prefix `dmarcdeliv-`. SHA-pin actions.

```yaml
name: dmarcdeliv-ci
on:
  push:
    paths: ["dmarcdeliv/**", "examples/**", ".github/workflows/dmarcdeliv-*.yml"]
  pull_request:
    paths: ["dmarcdeliv/**", "examples/**", ".github/workflows/dmarcdeliv-*.yml"]
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      DMARCDELIV_LIVE_DNS: "0"
      DMARCDELIV_APPLY: "0"
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-groups
      - run: uv run ruff check dmarcdeliv tests
      - run: uv run pytest -q
      - run: uv run pip-audit --strict
      - uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: fs
          version: v0.71.2
          severity: HIGH,CRITICAL
          exit-code: "1"
```

- `dmarcdeliv-watch.yml` — Monday 09:00 AEST.
- `dmarcdeliv-auto-approve.yml` — bots only.
- `dmarcdeliv-rebase.yml` — bot rebase.
- `dmarcdeliv-monthly.yml` — `monthly/dmarc-posture.md`.
- `dmarcdeliv-keepalive.yml` — `dmarcdeliv/state/keepalive.txt`.

GitHub 2026-03-25 auto-merge 422 caveat. `.cursor/rules/dmarcdeliv-build.mdc`: 9-module DMARC+deliverability, parsedmarc+dnspython, RUF bodies dropped, no DNS apply without gates.

DNS fixture shape:

```json
{
  "domain": "example.com",
  "mx": ["example-com.mail.protection.outlook.com."],
  "spf": "v=spf1 include:spf.protection.outlook.com -all",
  "dmarc": "v=DMARC1; p=none; rua=mailto:dmarc@example.com",
  "dkim": [{"selector": "selector1", "present": true}],
  "bimi": null,
  "mta_sts_txt": "v=STSv1; id=20260907",
  "mta_sts_policy": "version: STSv1\nmode: testing\nmx: example-com.mail.protection.outlook.com\nmax_age: 86400\n",
  "tlsrpt": "v=TLSRPTv1; rua=mailto:tlsrpt@example.com"
}
```

Minimal RUA XML fixture (must parse):

```xml
<?xml version="1.0"?>
<feedback>
  <report_metadata>
    <org_name>google.com</org_name>
    <email>noreply-dmarc-support@google.com</email>
    <report_id>fixture-1</report_id>
    <date_range><begin>1757203200</begin><end>1757289600</end></date_range>
  </report_metadata>
  <policy_published>
    <domain>example.com</domain>
    <p>none</p><sp>none</sp><pct>100</pct>
  </policy_published>
  <record>
    <row>
      <source_ip>203.0.113.10</source_ip>
      <count>42</count>
      <policy_evaluated><disposition>none</disposition><dkim>pass</dkim><spf>pass</spf></policy_evaluated>
    </row>
    <identifiers><header_from>example.com</header_from></identifiers>
    <auth_results>
      <dkim><domain>example.com</domain><result>pass</result></dkim>
      <spf><domain>example.com</domain><result>pass</result></spf>
    </auth_results>
  </record>
</feedback>
```

Makefile:

```makefile
dmarcdeliv-audit-inventory:
	python -m dmarcdeliv audit inventory
dmarcdeliv-all:
	python -m dmarcdeliv audit inventory
	python -m dmarcdeliv dns check example.com --fixture examples/dns/example.com.json
	python -m dmarcdeliv ingest rua examples/rua/
	python -m dmarcdeliv alignment summary --fixture examples/
	python -m dmarcdeliv report build --domain example.com --out reports/
```

## 5. The 4-stage build order — commit as you go

**Stage 1 — scaffold.** Package, audit, DuckDB schema, `examples/dns/example.com.json`, `examples/rua/` (1-2 tiny aggregate XML), `examples/tlsrpt/`, CI. Check: `make dmarcdeliv-audit-inventory`.

**Stage 2 — dns + ingest.** Parser tests: SPF includes, DMARC `p=none`, one RUA XML → N rows. Check: `dmarcdeliv ingest rua examples/rua/`.

**Stage 3 — alignment + sources + threats + tls + blacklist.** Golden: 80% pass alignment, one unknown source, MTA-STS testing, one DNSBL fixture hit. Check: `dmarcdeliv alignment summary --fixture examples/`.

**Stage 4 — report + loop.** HTML+MD+JSON with SHA-256 and **draft** TXT records (`v=DMARC1; p=quarantine; pct=10; ...`) clearly marked DRAFT. Check: `make dmarcdeliv-all`. Tests fail if RUF body fields are persisted.

## 6. The forum-watcher sources extension

```yaml
- name: r/sysadmin
  url: https://www.reddit.com/r/sysadmin/.rss
  module_hint: dmarcdeliv/dns, dmarcdeliv/report
  max_items: 25
- name: r/msp
  url: https://www.reddit.com/r/msp/.rss
  module_hint: dmarcdeliv/report
  max_items: 25
- name: r/DMARC
  url: https://www.reddit.com/r/DMARC/.rss
  module_hint: dmarcdeliv/alignment, dmarcdeliv/ingest
  max_items: 25
- name: parsedmarc-releases
  url: https://github.com/domainaware/parsedmarc/releases.atom
  module_hint: dmarcdeliv/ingest
  max_items: 10
- name: dnspython-releases
  url: https://github.com/rthalley/dnspython/releases.atom
  module_hint: dmarcdeliv/dns
  max_items: 10
```

HN: `dmarc`, `mta-sts`, `bimi`, `spf flattening`. Skip Valimail/dmarcian/Red Sift OnDMARC commercial Evaluate hits unless they publish an OSS parser change.

## 7. The free-LLM classification prompt

Gemini Flash. Input: domain, current `p=`, alignment %, top failing org **name** (not IP list dumps).

```json
{
  "finding_id": "string",
  "client_summary": "string, <= 40 words",
  "next_dmarc_step": "stay_none|pct_up|quarantine|reject",
  "human_action": "draft DNS change, do not apply"
}
```

Never paste raw RUF XML into the model.

## 8. The auto-PR / conflict / issue-fix patterns

Bot-only auto-approve. Rebase-only. `good first issue` only. Do not auto-fix recommended DNS strings that change `p=` (operator-owned policy ladder).

## 9. The 5-stage loop wiring

Discover = watcher + parsedmarc/dnspython releases + RFC errata feeds if cheap. Evaluate ≥ 7. Integrate Monday. Validate pytest (no live DNS in CI). Compound = monthly % aligned and `p=` ladder progress.

## 10. The cost ceiling

$0/month. No dmarcian, Valimail, OnDMARC, Proofpoint EFD. No Elasticsearch default. DNSBL live lookups optional and cached. Customer already receives RUA at a mailbox they control.

## 11. The eight hard rules

1. No paid DMARC SaaS.
2. No GPU/Ollama.
3. Do not break PR handoff.
4. Trivy 0.71.2 / 0.70+ (CVE-2026-33634).
5. Drop RUF message bodies; aggregate + TLS-RPT only by default.
6. No DNS provider apply without dual gates + allow-list.
7. Dedupe Discover by SHA-256 URL.
8. In-repo keepalive.

Plus: offline fixtures in CI; SPF flattening drafts must warn about 10-lookup limit; BIMI requires `p=quarantine` or `reject` — do not recommend BIMI at `p=none`; SHA-pin Actions.

## 12. The completion criteria

Four stages committed. `make dmarcdeliv-all` on fixtures. Report HTML+MD+JSON with SHA-256 and DRAFT DNS. Tests prove RUF bodies are not stored. Watch + bot auto-approve present. `.cursor/rules/dmarcdeliv-build.mdc` present. Live DNS/IMAP optional.

## 13. The anti-patterns to avoid

- Do not use Sonnet/Opus for scaffolding.
- Do not require Elasticsearch/Kibana.
- Do not store forensic email content.
- Do not auto-publish DNS.
- Do not jump `p=none` → `p=reject` in one draft; use a ladder (`pct`, then quarantine, then reject).
- Do not DNSBL-query every RUA IP by default.
- Do not auto-approve human PRs.
- Do not send raw XML to an LLM.
- Do not reimplement mailbox DSPM; this product is authentication/reporting.

## 14. The single takeaway

**dnspython reads the records, parsedmarc eats RUA/TLS-RPT, DuckDB scores alignment, Jinja writes the MSP pack with draft DNS.** It is not Valimail. Honest gap: ~50-70% of commercial deliverability (no seed-list inbox placement, no BIMI VMC procurement, no ESP-specific warm-up). At $0/month it is the right quarterly email-auth review for AU SMBs. Paste this whole message into Composer, set Max, scaffold `dmarcdeliv/`, commit as you go.

[model used: Composer/Grok] [Bucket: B] [module: dmarcdeliv]
