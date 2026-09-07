You are extending an existing 16-module tape-to-cloud migration tool and its 12-module DSPM sibling (the prior 11 turns of build context) with a new sibling project: an **SSPM-as-report** tool — SaaS Security Posture Management that produces a client-ready findings pack for a 1-person Australian MSP. Build it entirely from open-source components, with continuous forum-driven feature discovery, automatic PR approval for bot PRs, automatic conflict resolution, automatic issue fixing, and the 5-stage improvement loop. Primary engine: **Mondoo cnspec** (CLI, policy-as-code in MQL) against Microsoft 365, Google Workspace, GitHub, GitLab, Slack, Okta, Zoom, and Cloudflare. The 95/5 model discipline routes scaffolding and classification to Grok Code Fast / Composer 2.5 Standard / `gemini-2.5-flash` (free tier, 10 RPM, 250 RPD, no card) and reserves Claude Sonnet 5 / Opus 5 / Fable 5.1 only for named hard triggers. Total monthly cost: $0. This is a **report product**, not an auto-remediator.

## 0. Read first

Before writing any code, read every file in `/workspace/mavis-deep-research/` (the prior turns of context). Then read, if present:

- `discovery/tape-to-cloud/cursor-prompt.md`
- `discovery/tape-to-cloud/continuous-improvement-loop-prompt.md`
- `discovery/tape-to-cloud/free-tool-inventory.md`
- `discovery/dspm/cursor-prompt.md` and `dspm/README.md` (DSPM is the sibling — copy its CLI/loop/CI patterns, do not reimplement DSPM)
- `forum-watcher/sources.yaml` and `forum-watcher/scripts/watch.py`
- `.cursor/rules/tape-to-cloud-build.mdc`
- `.cursor/rules/tape-to-cloud-improvement-loop.mdc`
- `.cursor/rules/dspm-build.mdc` or `.cursor/rules/dspm-cyera-build.mdc` if they exist on the branch

Do not re-implement tape-to-cloud, DSPM, the forum-watcher, or the Bugbot replacement (`prek` + Ruff + zizmor + OSV-Scanner + actionlint). Do not break `peter-evans/create-pull-request@v8` or `hmarr/auto-approve-action@v4`. Do **not** use `gautamkrishnar/keepalive-workflow` (repo disabled); keep scheduled workflows alive with an in-repo weekly timestamp at `sspm/state/keepalive.txt`. Do not introduce paid services, GPU/Ollama, or cloud APIs that bill. SHA-pin every GitHub Action (`uses: owner/action@<commit-sha>  # vX.Y.Z`). Cron timezone is `Australia/Sydney` (Monday 09:00 AEST). Steampipe, if used as a fallback inventory, is a **CLI subprocess only** (AGPL-3.0). Never `import steampipe`.

Operator: 1-person AU MSP. Customers: AU SMBs who cannot afford Adaptive / Obsidian / AppOmni. Output is a **draft report for human review**, not regulated advice. Do not store mailbox bodies, Drive file contents, Slack messages, or raw PII — metadata and posture findings only.

## 1. The 12-module architecture

Create a Python package `sspm/` with exactly these 12 modules. Each module ships with `cli.py` (Typer), `service.py`, `models.py` (Pydantic v2), `tests/`, and a `README.md` (≤ 200 words). JSON output by default; `--human` for a table. Fixture-first: every connector must run against `examples/` without live SaaS credentials.

1. `sspm/audit/` — tool + license inventory. Output: `sspm-inventory.json` listing every OSS tool, version, license, last-update. CLI: `sspm audit inventory`. **Primary tool: `pip-audit` + OSV.dev.**
2. `sspm/discovery/` — SaaS tenant inventory. Enumerate connected tenants from a YAML registry (`sspm/discovery/tenants.yaml`: kind, tenant id, credential env-var names). Also detect shadow SaaS from DNS MX/SPF includes, IdP app catalogs, and browser-extension CSV exports. Output: Postgres/`findings_tenants`. CLI: `sspm discovery list` and `sspm discovery dns example.com`. **Primary tool: Mondoo cnspec providers + dnspython for shadow hints. Honest gap: no browser-plugin CASB.**
3. `sspm/posture/` — cnspec policy scans. Wrap `cnspec scan` as a subprocess. Open-source users pass local/URL policy bundles (never require Mondoo Platform). Providers: `ms365`, `google-workspace`, `github org`, `gitlab`, `slack`, `okta`, `zoom`, `cloudflare`. Output: `findings_posture` from cnspec JSON. CLI: `sspm posture scan --provider ms365 --fixture examples/cnspec/ms365.json`. **Primary tool: cnspec CLI. Bundles: `mondoo-m365-security.mql.yaml`, `mondoo-github-security.mql.yaml`, `mondoo-google-workspace-security.mql.yaml` from `mondoohq/cnspec` `content/`.**
4. `sspm/identity/` — MFA coverage, unused accounts, admin-role sprawl, SSO gaps. Merge cnspec identity checks with Microsoft Graph / Google Admin / GitHub org membership fixtures. Output: `findings_identity`. CLI: `sspm identity report --tenant acme`. **Honest gap: no unified identity graph like AppOmni.**
5. `sspm/sharing/` — external sharing, guest users, public links, anonymous access (SharePoint/Drive/Dropbox/GitHub). Fixtures under `examples/sharing/`. CLI: `sspm sharing scan`. **Do not download file contents.**
6. `sspm/oauth/` — shadow OAuth apps, over-privileged Graph/Google/Slack grants, unused enterprise apps. CLI: `sspm oauth apps`. **Primary: Graph `servicePrincipals` + Google tokens + Slack apps, fixture JSON. Honest gap: no runtime token replay.**
7. `sspm/misconfig/` — tenant baselines vs CIS / CISA / Essential Eight / ACSC. YAML control map at `sspm/misconfig/baselines.yaml`. CLI: `sspm misconfig check --framework essential8`.
8. `sspm/secrets/` — tokens in GitHub (gitleaks/TruffleHog on a cloned fixture repo), Slack webhook URLs in fixtures, PATs in org audit logs (metadata only). CLI: `sspm secrets scan examples/repos/`. **Never persist live secret values; fingerprint + location only.**
9. `sspm/compliance/` — map findings to ISO 27001 / SOC 2 / Essential Eight / GDPR (access-control clauses only). YAML at `sspm/compliance/controls.yaml`. CLI: `sspm compliance map --framework essential8`. **Honest gap: hand-maintained mappings. Not a certification.**
10. `sspm/risk/` — DuckDB SQL score over `posture ∪ identity ∪ sharing ∪ oauth ∪ secrets`. Weights: public sharing=25, no-MFA admin=25, over-privileged OAuth=20, secrets=15, baseline miss=15. CLI: `sspm risk score --since 7d`. **Primary tool: duckdb. Formula is local SQL, not ML.**
11. `sspm/report/` — **the product**. HTML + Markdown + JSON pack: executive summary, top-10 risks, per-SaaS scorecards, evidence appendix, watermark (SHA-256 of canonical JSON). Free tier redacts entry-level evidence older than 24h is N/A here — instead Free = summary only, Pro = full evidence. CLI: `sspm report build --client acme --out reports/`. **No Flask/FastAPI; stdlib http.server optional. Static HTML is the deliverable.**
12. `sspm/remediation/` — runbooks and ticket drafts, not auto-apply. Output: `remediation_plan.json` with `target`, `action`, `preconditions`, `risk_level`, `dry_run_safe`. CLI: `sspm remediate plan --dry-run`. Ship 4 markdown runbooks: enforce MFA, revoke stale guest, tighten sharing, remove unused OAuth. **Never call Graph/Slack/GitHub mutating APIs unless `--apply` and `SSPM_APPLY=1`.**

A 13th module, `sspm/loop/`, is the watcher payload: reuse `forum-watcher/scripts/watch.py`, extend `sources.yaml`, Monday 09:00 AEST cron. Do not duplicate the watcher.

## 2. The `pyproject.toml`

```toml
[project]
name = "sspm"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "duckdb>=1.2.0",
  "pyarrow>=17.0.0",
  "httpx>=0.27.0",
  "pydantic>=2.9.0",
  "typer>=0.15.0",
  "pyyaml>=6.0.2",
  "feedparser>=6.0.11",
  "rich>=13.9.0",
  "dnspython>=2.7.0",
  "jinja2>=3.1.4",
]
# cnspec, gitleaks, trivy are CLI binaries, not pip packages.
# Optional live connectors (never required for pytest):
#   msgraph-sdk, slack-sdk, PyGithub, google-api-python-client

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-cov>=6.0.0",
  "ruff>=0.9.0",
  "mypy>=1.14.0",
  "pip-audit>=2.7.0",
]
graph = ["msgraph-sdk", "azure-identity"]
slack = ["slack-sdk"]
github = ["PyGithub"]

[project.scripts]
sspm = "sspm.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Install cnspec as a documented CLI (GitHub release binary or container). Wrap it in `sspm/posture/cnspec.py` with a `which("cnspec")` check and a fixture fallback when the binary is missing. Same pattern DSPM used for Steampipe/Prowler.

## 3. The `docker-compose.yml` for local dev

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: sspm
      POSTGRES_PASSWORD: sspm
      POSTGRES_DB: sspm
    ports: ["5433:5432"]
    volumes: [sspm-pg:/var/lib/postgresql/data]
  cnspec:
    image: mondoo/cnspec:latest
    entrypoint: ["cnspec", "version"]
    profiles: ["tools"]
volumes:
  sspm-pg:
```

Do not pull Trivy 0.69.4 images. If you add a scanner sidecar, pin Trivy **0.71.2 / 0.70+** (CVE-2026-33634). MinIO Community Edition is archived (2026-04-25); do not add it.

## 4. The GitHub Actions workflows

SHA-pin every action. Copy the DSPM workflow pattern with `sspm-` prefixes.

### 4.1 `sspm-ci.yml`

Runs on every push/PR touching `sspm/**`, `examples/**`, `.github/workflows/sspm-*.yml`. Jobs: `uv`/`pip` install `.[dev]`, `ruff check`, `ruff format --check`, `mypy sspm`, `pytest -q`, `pip-audit`, `trivy fs --severity HIGH,CRITICAL` with Trivy 0.71.2, `actionlint` + `zizmor` on the sspm workflows. Fixture-only: no live M365/GitHub tokens in CI.

### 4.2 `sspm-watch.yml`

Monday 09:00 AEST:

```yaml
on:
  schedule:
    - cron: "0 9 * * 1"
      timezone: "Australia/Sydney"
  workflow_dispatch:
```

Run `python -m sspm loop improve` (or `forum-watcher/scripts/watch.py` with `sspm/loop/sources.yaml`). Open a Discover PR via `peter-evans/create-pull-request@v8`.

### 4.3 `sspm-auto-approve.yml`

`pull_request_target`. Approve **only** `dependabot[bot]` and `github-actions[bot]`. Never auto-approve human PRs. Never auto-merge files under `sspm/remediation/`. GitHub 2026-03-25: `gh pr merge --auto` returns HTTP 422 unless required checks already exist — wire `sspm-ci.yml` as a required check.

### 4.4 `sspm-rebase.yml`

Rebase bot PRs onto main. On conflict, comment `@operator merge conflict — please resolve manually` and exit non-zero. No force-push to human branches.

### 4.5 `sspm-monthly.yml`

First Monday 09:00 AEST rollup → `monthly/YYYY-MM.md` + `monthly/saas-posture.md`.

### 4.6 `sspm-keepalive.yml`

Weekly write `sspm/state/keepalive.txt` (ISO timestamp). Do not use `gautamkrishnar/keepalive-workflow`.

### 4.7 `.cursor/rules/sspm-build.mdc`

Agent Requested. Description: 12-module SSPM-as-report, cnspec CLI, $0/month, fixture-first, no mutating SaaS APIs without `SSPM_APPLY=1`.

## 5. The 4-stage build order — commit as you go

Do not start stage N+1 until stage N CI is green.

**Stage 1 — scaffold.** `pyproject.toml`, `sspm/cli.py`, `sspm/audit/`, `sspm/db/schema.sql`, `examples/tenants.yaml`, `examples/cnspec/*.json` (synthetic cnspec scan JSON for M365 + GitHub), workflows `sspm-ci.yml` + `sspm-keepalive.yml`, Makefile targets `sspm-audit-inventory`, `sspm-all`. Operator check: `make sspm-audit-inventory` lists 12 modules + cnspec.

**Stage 2 — discovery + posture.** `sspm/discovery/` + `sspm/posture/` with fixture parser. If cnspec binary exists, optional live scan behind `--live`. Operator check: `sspm posture scan --fixture examples/cnspec/ms365.json` emits ≥5 findings.

**Stage 3 — identity + sharing + oauth + risk.** DuckDB formula unit test with known input → known score. Operator check: `sspm risk score` ranks "guest link + no MFA" at the top.

**Stage 4 — secrets + compliance + report + remediation + loop.** `sspm report build` writes HTML+MD+JSON with SHA-256 watermark. Forum-watcher sources extended. Operator check: `make sspm-all` and open `reports/sspm_explorer.html`.

## 6. The forum-watcher sources extension

Append (do not replace) `forum-watcher/sources.yaml`:

```yaml
- name: r/msp
  url: https://www.reddit.com/r/msp/.rss
  module_hint: sspm/report, sspm/identity
  max_items: 25
- name: r/sysadmin
  url: https://www.reddit.com/r/sysadmin/.rss
  module_hint: sspm/misconfig, sspm/oauth
  max_items: 25
- name: r/cybersecurity
  url: https://www.reddit.com/r/cybersecurity/.rss
  module_hint: sspm/posture, sspm/risk
  max_items: 25
- name: cnspec-releases
  url: https://github.com/mondoohq/cnspec/releases.atom
  module_hint: sspm/posture
  max_items: 10
- name: prowler-releases
  url: https://github.com/prowler-cloud/prowler/releases.atom
  module_hint: sspm/misconfig
  max_items: 10
```

Also watch HN queries `sspm`, `saas security posture`, `cnspec`, `appomni`, Stack Overflow tags `microsoft-graph`, `google-admin-sdk`. Dedupe Discover items by SHA-256 of the canonical URL.

## 7. The free-LLM classification prompt

Gemini Flash (or Grok) only. Use for: (a) mapping a cnspec check title to a client-friendly finding paragraph, (b) Discover-item module-fit scores, (c) monthly rollup prose. Schema:

```json
{
  "finding_id": "string",
  "client_summary": "string, <= 40 words, no CVE dump",
  "severity": "info|low|medium|high|critical",
  "module": "posture|identity|sharing|oauth|secrets|misconfig",
  "human_action": "string, draft only"
}
```

Validate with Pydantic. On schema fail, abstain (`verdict: abstain`). Never send tenant IDs, emails, or tokens to the model — hash or redact first.

## 8. The auto-PR / conflict / issue-fix patterns

Same as DSPM: bot-only auto-approve; rebase-only conflict resolution; `good first issue` mechanical fixes via `peter-evans/create-pull-request@v8`. Do not auto-fix issues that change remediation runbooks or live-connector scopes.

## 9. The 5-stage loop wiring

- **Discover** = forum-watcher + cnspec/Prowler/gitleaks releases + Dependabot.
- **Evaluate** = 4-axis rubric (module-fit, signal, license, actionability), threshold ≥ 7. Skip Adaptive/Obsidian/AppOmni/Wiz commercial pitches.
- **Integrate** = Monday operator review + bot PR auto-approve.
- **Validate** = pytest + ruff + pip-audit + trivy fs.
- **Compound** = monthly `saas-posture.md` trend: MFA coverage up? guest links down? OAuth grants down?

## 10. The cost ceiling

$0/month. GitHub Actions free tier, Gemini Flash free tier, cnspec OSS CLI, DuckDB, dnspython. Customer IdP/SaaS APIs are the customer's existing tenants — no extra SaaS bill. Mondoo Platform is optional and **out of scope**; OSS policy-bundle URLs only.

## 11. The eight hard rules

1. No new paid services. No Mondoo Platform requirement.
2. No GPU, no Ollama.
3. Do not break the existing PR handoff.
4. Trivy 0.71.2 / 0.70+ only (never 0.69.4 — CVE-2026-33634).
5. Steampipe CLI subprocess only if used (AGPL-3.0).
6. cnspec is a CLI subprocess; parse JSON; never vendor Mondoo proprietary APIs.
7. Dedupe Discover items by SHA-256 of canonical URL.
8. In-repo keepalive timestamp weekly. No disabled third-party keepalive action.

Plus product rules: metadata-only (no mailbox/Drive/Slack bodies); `--apply` off by default; reports are drafts for human review; SHA-pin Actions; `uv` preferred, else `.venv`.

## 12. The completion criteria

Done when all 4 stages are committed, `make sspm-all` runs every module on fixtures, `sspm report build` writes HTML+MD+JSON with a verifying SHA-256, pytest covers fixture parsers for M365/GitHub/Slack, the watch workflow is present with Monday 09:00 AEST, auto-approve is bot-only, and `.cursor/rules/sspm-build.mdc` exists. Live API calls are optional extras, not completion gates.

## 13. The anti-patterns to avoid

- Do not route every LLM call through Sonnet/Opus.
- Do not add Slack/Discord webhooks as the delivery channel; the report files + PR are the channel.
- Do not require a paid SSPM (AppOmni, Adaptive, Obsidian, Microsoft Defender for Cloud Apps).
- Do not `import steampipe` or link cnspec as a library.
- Do not install Trivy 0.69.x.
- Do not store message bodies, file bytes, or live secrets.
- Do not auto-apply Graph/Slack/GitHub mutations.
- Do not auto-approve human PRs.
- Do not auto-merge `sspm/remediation/`.
- Do not scrape comment threads; RSS summaries are enough.
- Do not ship without `pip-audit` + trivy fs in CI.
- Do not reimplement DSPM classification/Presidio; this product is SaaS *configuration* posture, not data classification.

## 14. The single takeaway

The build is a 12-module mosaic: **cnspec does the SaaS scans, DuckDB scores, Jinja writes the client pack**. It is not AppOmni. Honest gap is ~60-75% of commercial SSPM (no identity graph, no inline CASB, no live token analytics). At $0/month it is the right MSP report engine for AU SMBs, and the 5-stage loop closes the gap. Paste this whole message into Composer, set Max, scaffold `sspm/`, commit as you go.

[model used: Composer/Grok] [Bucket: B] [module: sspm]
