# Four Safe Builds — Cursor Composer Prompts

Paste-oriented sibling of the DSPM-like-Cyera build. Each standalone file in this directory is the **raw prompt body only** (no outer fence, no `## N.` framing heading). Open a fresh repo, paste the entire file into Cursor Composer, set plan to **Max**, hit Enter.

These four are the remaining **safe** MSP report products after DSPM (data classification) landed: they do not store sensitive PII contents, they do not give regulated advice (drafts for human review), they run at **$0/month**, and they reuse the tape-to-cloud / DSPM loop (forum-watcher, bot auto-approve, Monday 09:00 AEST, 5-stage Discover → Evaluate → Integrate → Validate → Compound).

Operator: 1-person Australian MSP, AU SMB customers. DSPM is the fifth sibling (already implemented on branches `cursor/dspm-cyera-oss-5be8` / `cursor/dspm-cyera-build-08b7`). Do not re-prompt DSPM here.

## Why these four

| # | Product | Why it is "safe" | Primary OSS | Honest commercial analogue |
|---|---------|------------------|-------------|----------------------------|
| 1 | SSPM-as-report | SaaS *configuration* posture; no mailbox/Drive bodies | Mondoo cnspec | AppOmni / Adaptive / Defender for Cloud Apps |
| 2 | Cloud Cost & Config | Spend + CIS; c7n notify/mark-for-op only | Prowler + Steampipe CLI + Cloud Custodian | CloudHealth / Wiz (misconfig slice) |
| 3 | SaaS License & Spend | Seat metadata only; hashed emails | MS Graph + Slack SDK + PyGithub | Zylo / Productiv / Torii |
| 4 | DMARC + Deliverability | RUA counts; RUF bodies dropped | parsedmarc + dnspython | Valimail / dmarcian / OnDMARC |

DSPM remains the data-classification sibling (Presidio, CloudQuery, Trivy 0.71.2). These four must not reimplement Presidio NER.

## How to use in Cursor

1. `mkdir sspm && cd sspm && git init` (or `costreview` / `licensespend` / `dmarcdeliv`)
2. Open the folder in Cursor
3. Press **Cmd+I** (Composer)
4. Open the matching `0N-*-CURSOR-PROMPT.md`, select all, copy, paste
5. Set plan to **Max**, hit Enter
6. Composer reads prior turns from `/workspace/mavis-deep-research/` (Section 0) plus DSPM/tape-to-cloud rules if this repo is the workspace

Each prompt is self-contained. Inner YAML/TOML/XML/code fences are part of the prompt body.

## Shared hard gates (all four)

- $0/month. No paid SSPM/FinOps/SaaS-management/DMARC vendors.
- SHA-pin GitHub Actions. Trivy **0.71.2 / 0.70+** only (never 0.69.4 — CVE-2026-33634).
- Steampipe is a **CLI subprocess** (AGPL-3.0). Never `import steampipe`.
- Keepalive is an **in-repo timestamp** (`state/keepalive.txt`). Do not use `gautamkrishnar/keepalive-workflow` (disabled).
- Bot-only auto-approve (`dependabot[bot]`, `github-actions[bot]`). Never auto-merge remediation/DNS/apply paths.
- GitHub 2026-03-25: `gh pr merge --auto` returns HTTP 422 unless required checks already exist.
- Monday 09:00 AEST cron (`timezone: Australia/Sydney`).
- 95/5 routing: Grok Code Fast / Composer 2.5 Standard / Gemini Flash for ~95%. Sonnet/Opus/Fable only on named triggers.
- Mutating APIs (`--apply`) default off and dual-gated with an env flag + allow-list file.
- Reports are drafts for human review, not regulated advice.

## Prior 11 turns (Section 0)

Composer should read, in this repo:

1. `mavis-deep-research/20260907_131128_tape_to_cloud_cursor_prompt/final_turn_001.md`
2. `mavis-deep-research/20260907_continuous_improvement_loop/final_turn_001.md`
3. `mavis-deep-research/20260907_free_tool_inventory/final_turn_001.md`
4. `mavis-deep-research/20260907_bugbot_replacement/final_turn_001.md`
5. `discovery/tape-to-cloud/cursor-prompt.md`
6. `discovery/tape-to-cloud/continuous-improvement-loop-prompt.md`
7. `discovery/tape-to-cloud/free-tool-inventory.md`
8. `discovery/tape-to-cloud/tape-to-cloud-migration-blueprint.md`
9. `forum-watcher/scripts/watch.py` + `forum-watcher/sources.yaml`
10. DSPM sibling (`discovery/dspm/`, `dspm/`, `.cursor/rules/dspm*.mdc` on feature branches)
11. This directory — the four prompts below

## Files

| File | Size | Build |
|------|-----:|-------|
| `01-SSPM-CURSOR-PROMPT.md` | 16.3 KB | SSPM-as-report (12 modules, Mondoo cnspec) |
| `02-CLOUD-COST-CONFIG-CURSOR-PROMPT.md` | 15.0 KB | Cloud Cost & Config Review (10 modules, Prowler + Steampipe + Cloud Custodian) |
| `03-SAAS-LICENSE-CURSOR-PROMPT.md` | 13.6 KB | SaaS License & Spend (8 modules, MS Graph + Slack SDK + PyGithub) |
| `04-DMARC-DELIVERABILITY-CURSOR-PROMPT.md` | 14.0 KB | DMARC + Email Deliverability (9 modules, parsedmarc + dnspython) |

---

## 1. SSPM-as-report

Source file: `01-SSPM-CURSOR-PROMPT.md` — paste the block as a new Composer message.

```
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
```

---

## 2. Cloud Cost & Config Review

Source file: `02-CLOUD-COST-CONFIG-CURSOR-PROMPT.md` — paste the block as a new Composer message.

```
You are extending an existing 16-module tape-to-cloud migration tool and its 12-module DSPM sibling (the prior 11 turns of build context) with a new sibling project: a **Cloud Cost & Config Review** tool — an MSP-ready FinOps + CSPM report pack for AWS / Azure / GCP. Build it entirely from open-source components, with continuous forum-driven feature discovery, automatic PR approval for bot PRs, automatic conflict resolution, automatic issue fixing, and the 5-stage improvement loop. Primary engines: **Prowler** (config/CIS), **Steampipe** (SQL inventory + Thrifty mods, CLI only), **Cloud Custodian** (policy-as-code waste/tag/off-hours). The 95/5 model discipline routes scaffolding to Grok Code Fast / Composer 2.5 Standard / `gemini-2.5-flash` (free tier) and reserves Claude Sonnet 5 / Opus 5 / Fable 5.1 for named hard triggers only. Total monthly cost: $0. This is a **review report**, not an auto-reaper.

## 0. Read first

Before writing any code, read every file in `/workspace/mavis-deep-research/`. Then read, if present:

- `discovery/tape-to-cloud/cursor-prompt.md`
- `discovery/tape-to-cloud/continuous-improvement-loop-prompt.md`
- `discovery/tape-to-cloud/free-tool-inventory.md`
- `discovery/dspm/cursor-prompt.md` and `dspm/README.md` (copy CLI/loop/CI; do not reimplement DSPM)
- `4-safe-builds-prompts/01-SSPM-CURSOR-PROMPT.md` (sibling report product — share loop/CI patterns, different engines)
- `forum-watcher/sources.yaml` and `forum-watcher/scripts/watch.py`
- `.cursor/rules/tape-to-cloud-build.mdc`
- `.cursor/rules/dspm-build.mdc` or `.cursor/rules/dspm-cyera-build.mdc` if present

Do not re-implement tape-to-cloud, DSPM, SSPM, the forum-watcher, or the Bugbot replacement. Do not break `peter-evans/create-pull-request@v8` or `hmarr/auto-approve-action@v4`. Do **not** use `gautamkrishnar/keepalive-workflow` (disabled); keep cron alive with `costreview/state/keepalive.txt`. SHA-pin every GitHub Action. Cron timezone: `Australia/Sydney`, Monday 09:00 AEST.

**Steampipe is AGPL-3.0.** Use it as a CLI subprocess only. Never `import steampipe`. Never wrap Steampipe in a hosted multi-tenant SaaS without legal sign-off.

Operator: 1-person AU MSP. Customers: AU SMBs with one or two cloud accounts. Output is a **draft review for human approval**. Cloud Custodian policies ship in **notify/mark-for-op dry-run mode**. Destructive `stop`/`delete`/`terminate` actions require `--apply` **and** `COSTREVIEW_APPLY=1` **and** a matching `allow-apply.txt` resource id. Default is report-only.

## 1. The 10-module architecture

Create a Python package `costreview/` with exactly these 10 modules. Each: `cli.py` (Typer), `service.py`, `models.py` (Pydantic v2), `tests/`, `README.md` (≤ 200 words). JSON default; `--human` for a table. Fixture-first: pytest never needs live cloud credentials.

1. `costreview/audit/` — tool + license inventory (`pip-audit`, Prowler/Steampipe/c7n versions). CLI: `costreview audit inventory`.
2. `costreview/inventory/` — account/subscription/project catalog from Steampipe JSON or aws-cli/az/gcloud fixtures. Output: `findings_accounts`. CLI: `costreview inventory list --fixture examples/steampipe/aws_accounts.json`. **Primary: `steampipe query` subprocess. Fallback: boto3/azure-identity/google-cloud-resource-manager only as optional extras.**
3. `costreview/cost/` — CUR / Cost Explorer / Azure Cost Management / GCP billing export **fixtures** (CSV/Parquet). DuckDB over `line_item` tables: last-30d spend by service, account, tag. CLI: `costreview cost summarize --since 30d`. **Honest gap: no real-time billing API in OSS without customer credentials; fixtures prove the math.**
4. `costreview/idle/` — idle EC2/VM/SQL, unused load balancers, idle NAT. Steampipe AWS Thrifty / Azure Thrifty query JSON **or** CloudWatch metric fixtures. CLI: `costreview idle scan`. Thresholds in `costreview/idle/thresholds.yaml` (CPU < 5% for 7d, etc.).
5. `costreview/rightsizing/` — oversized instances / unattached GPUs / gp2→gp3. Recommendations only (`suggested_type`, `est_monthly_save_usd`). CLI: `costreview rightsize recommend`. **Never resize in-place.**
6. `costreview/config/` — Prowler CIS/FSBP findings. Wrap `prowler aws --severity high critical --output json`. Fixture parser for `examples/prowler/*.json`. CLI: `costreview config scan --fixture examples/prowler/aws.json`. **Primary: prowler Apache-2.0. Honest gap: ~75-85% of Wiz misconfig coverage.**
7. `costreview/waste/` — unattached EBS/disks, unused Elastic IPs, old snapshots, unused AMIs, unattached public IPs, idle Elastic IPs, leftover CloudWatch log groups. CLI: `costreview waste scan`. **Primary: Cloud Custodian dry-run + Steampipe.**
8. `costreview/tagging/` — missing `Owner`/`Environment`/`CostCenter` tags; mark-for-op **as a report row**, not a live tag. CLI: `costreview tagging audit`. YAML required-tags at `costreview/tagging/policy.yaml`.
9. `costreview/report/` — **the product**. HTML + Markdown + JSON: executive savings, top waste, CIS fails, tag coverage, SHA-256 watermark. CLI: `costreview report build --client acme --out reports/`. Static HTML; no Flask/FastAPI.
10. `costreview/remediation/` — Cloud Custodian YAML, **notify + mark-for-op only** in the shipped set. Four policies: `c7n-ebs-unattached-mark.yaml`, `c7n-eip-unused-notify.yaml`, `c7n-ec2-idle-notify.yaml`, `c7n-snapshot-old-notify.yaml`. CLI: `costreview remediate plan --dry-run` and `c7n-policy validate` in tests. **Do not auto-merge this directory. Do not `c7n run` with delete/stop unless both apply gates are set.**

A 11th module `costreview/loop/` reuses the forum-watcher. Do not duplicate it.

## 2. The `pyproject.toml`

```toml
[project]
name = "costreview"
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
  "jinja2>=3.1.4",
  "c7n>=0.9.40",
]
# prowler and steampipe are CLI binaries. Optional:
#   prowler (pip package exists — pin and wrap; still prefer CLI JSON)
#   boto3, azure-identity, google-cloud-billing — extras only

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-cov>=6.0.0",
  "ruff>=0.9.0",
  "mypy>=1.14.0",
  "pip-audit>=2.7.0",
]
aws = ["boto3"]
azure = ["azure-identity", "azure-mgmt-costmanagement"]
gcp = ["google-cloud-billing"]

[project.scripts]
costreview = "costreview.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Wrap `steampipe` and `prowler` like DSPM: `which` + subprocess + fixture fallback. Parse JSON; do not scrape stdout tables.

## 3. The `docker-compose.yml` for local dev

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: costreview
      POSTGRES_PASSWORD: costreview
      POSTGRES_DB: costreview
    ports: ["5434:5432"]
volumes:
  costreview-pg:
```

No MinIO (archived 2026-04-25). No LocalStack requirement; fixtures are enough. If you add LocalStack later, keep it optional and out of default `make costreview-all`.

## 4. The GitHub Actions workflows

Prefix `costreview-`. SHA-pin actions. Mirror DSPM/SSPM.

`costreview-ci.yml`:

```yaml
name: costreview-ci
on:
  push:
    paths: ["costreview/**", "examples/**", ".github/workflows/costreview-*.yml"]
  pull_request:
    paths: ["costreview/**", "examples/**", ".github/workflows/costreview-*.yml"]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-groups
      - run: uv run ruff check costreview tests
      - run: uv run ruff format --check costreview tests
      - run: uv run mypy costreview
      - run: uv run pytest -q
      - run: uv run pip-audit --strict
      - uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: fs
          scan-ref: .
          severity: HIGH,CRITICAL
          exit-code: "1"
          version: v0.71.2
      - name: validate c7n policies
        run: |
          uv run python - <<'PY'
          from pathlib import Path
          import yaml, sys
          forbidden = {"delete", "terminate", "stop"}
          root = Path("costreview/remediation/policies")
          for p in root.glob("*.yaml"):
              doc = yaml.safe_load(p.read_text())
              for pol in doc.get("policies", [doc]):
                  for act in pol.get("actions") or []:
                      t = act if isinstance(act, str) else act.get("type")
                      if t in forbidden and "requires-apply" not in p.read_text():
                          sys.exit(f"destructive action {t} in {p}")
          print("c7n policies ok")
          PY
```

- `costreview-watch.yml` — Monday 09:00 AEST, `timezone: Australia/Sydney`.
- `costreview-auto-approve.yml` — bots only; never human; never auto-merge `costreview/remediation/policies/`.
- `costreview-rebase.yml` — bot rebase; comment on real conflicts.
- `costreview-monthly.yml` — first Monday rollup `monthly/cloud-cost.md`.
- `costreview-keepalive.yml` — weekly `costreview/state/keepalive.txt`.

GitHub 2026-03-25: `gh pr merge --auto` HTTP 422 unless required checks exist — register `costreview-ci`.

Makefile (required targets):

```makefile
costreview-audit-inventory:
	python -m costreview audit inventory
costreview-all:
	python -m costreview audit inventory
	python -m costreview cost summarize --fixture examples/cur/sample.csv
	python -m costreview config scan --fixture examples/prowler/aws.json
	python -m costreview waste scan --fixture examples/waste/
	python -m costreview report build --client fixture --out reports/
```

Shipped c7n example (notify only):

```yaml
policies:
  - name: ebs-unattached-notify
    resource: ebs
    comments: Report-only. No delete.
    filters:
      - Attachments: []
    actions:
      - type: notify
        subject: "[Cost] unattached EBS"
        to: [resource-owner]
        transport:
          type: sqs
          queue: https://sqs.ap-southeast-2.amazonaws.com/000000000000/c7n-mailer
```

`.cursor/rules/costreview-build.mdc`: 10-module cost+config review, Prowler + Steampipe CLI + c7n dry-run, $0/month, no destroy without dual apply gates.

## 5. The 4-stage build order — commit as you go

**Stage 1 — scaffold.** Package, audit module, schema, `examples/cur/sample.csv` (synthetic 30-day CUR-like rows), `examples/prowler/aws.json`, `examples/steampipe/thrifty.json`, CI + keepalive, Makefile. Check: `make costreview-audit-inventory`.

**Stage 2 — inventory + cost + config.** DuckDB spend-by-service matches a golden fixture total. Prowler JSON parser emits CIS fails. Check: `costreview cost summarize --fixture examples/cur/sample.csv`.

**Stage 3 — idle + rightsizing + waste + tagging.** Unit tests with known volumes/EIPs. Check: `costreview waste scan --fixture examples/waste/` lists unattached disks.

**Stage 4 — report + remediation + loop.** Four c7n YAML files **notify/mark-for-op only**. `costreview report build` HTML+MD+JSON with SHA-256. Check: `make costreview-all`. Policy tests fail if a shipped policy contains `type: delete` or `type: terminate` without a `# requires-apply` header that the loader strips unless gates are set.

## 6. The forum-watcher sources extension

```yaml
- name: r/aws
  url: https://www.reddit.com/r/aws/.rss
  module_hint: costreview/idle, costreview/waste
  max_items: 25
- name: r/FinOps
  url: https://www.reddit.com/r/FinOps/.rss
  module_hint: costreview/cost, costreview/rightsizing
  max_items: 25
- name: r/devops
  url: https://www.reddit.com/r/devops/.rss
  module_hint: costreview/config, costreview/tagging
  max_items: 25
- name: prowler-releases
  url: https://github.com/prowler-cloud/prowler/releases.atom
  module_hint: costreview/config
  max_items: 10
- name: steampipe-releases
  url: https://github.com/turbot/steampipe/releases.atom
  module_hint: costreview/inventory
  max_items: 10
- name: cloud-custodian-releases
  url: https://github.com/cloud-custodian/cloud-custodian/releases.atom
  module_hint: costreview/remediation
  max_items: 10
```

HN queries: `cloud custodian`, `prowler`, `steampipe`, `finops`, `idle ebs`. Dedupe by SHA-256 URL. Skip CloudHealth/Flexera/Umbrella commercial pitches in Evaluate.

## 7. The free-LLM classification prompt

Gemini Flash only. Inputs: Prowler check title + resource type (no account IDs, no ARNs with account numbers — mask to `arn:aws:...:************:...`). Output schema:

```json
{
  "finding_id": "string",
  "client_summary": "string, <= 40 words",
  "monthly_save_band": "none|low|<100|100-1k|>1k",
  "module": "idle|rightsizing|waste|config|tagging",
  "human_action": "string, draft only"
}
```

Abstain on schema fail. Never send billing CSVs wholesale; send aggregates.

## 8. The auto-PR / conflict / issue-fix patterns

Bot-only auto-approve. Rebase-only conflicts. `good first issue` mechanical fixes. Do not auto-fix c7n action verbs (`delete`/`stop`/`terminate`).

## 9. The 5-stage loop wiring

Discover = watcher + Prowler/Steampipe/c7n/Trivy releases. Evaluate = 4-axis rubric ≥ 7. Integrate = Monday review. Validate = pytest + c7n validate + trivy fs. Compound = monthly waste $ trend and CIS fail count.

## 10. The cost ceiling

$0/month. Customer cloud APIs are theirs. No CloudHealth, no AWS Trusted Advisor Business support requirement, no Steampipe Cloud, no Prowler Cloud. Trivy 0.71.2 in CI.

## 11. The eight hard rules

1. No paid FinOps/CSPM SaaS.
2. No GPU/Ollama.
3. Do not break PR handoff.
4. Trivy 0.71.2 / 0.70+ only (CVE-2026-33634).
5. Steampipe CLI only (AGPL-3.0).
6. Shipped c7n policies are notify/mark-for-op. Delete/stop need dual apply gates.
7. Dedupe Discover by SHA-256 URL.
8. In-repo keepalive timestamp.

Plus: never print full account IDs in HTML reports (mask middle); CUR fixtures contain no real customer billing; SHA-pin Actions.

## 12. The completion criteria

Four stages committed. `make costreview-all` on fixtures. Report HTML+MD+JSON with SHA-256. Tests refuse shipped destructive c7n actions without gates. Watch workflow Monday 09:00 AEST. Bot-only auto-approve. `.cursor/rules/costreview-build.mdc` present. Live AWS is optional.

## 13. The anti-patterns to avoid

- Do not use Sonnet/Opus for scaffolding.
- Do not add a web app; static report is the product.
- Do not `import steampipe`.
- Do not install Trivy 0.69.x.
- Do not ship `type: delete` as the default c7n action.
- Do not auto-merge remediation YAML.
- Do not auto-approve human PRs.
- Do not require AWS Organizations / Control Tower.
- Do not recommend MinIO CE (archived 2026-04-25).
- Do not send raw CUR files to an LLM.
- Do not reimplement DSPM Presidio classification; this product is spend + misconfig, not PII.

## 14. The single takeaway

**Prowler finds the misconfig, Steampipe SQL finds the idle spend, Cloud Custodian drafts the cleanup, DuckDB+Jinja write the MSP review.** It is not CloudHealth or Wiz. Honest gap: ~50-70% of commercial FinOps (no unit economics, no container rightsizing ML, no RI/SP marketplace). At $0/month it is the right quarterly cloud-review engine for AU SMBs. Paste this whole message into Composer, set Max, scaffold `costreview/`, commit as you go.

[model used: Composer/Grok] [Bucket: B] [module: costreview]
```

---

## 3. SaaS License & Spend

Source file: `03-SAAS-LICENSE-CURSOR-PROMPT.md` — paste the block as a new Composer message.

```
You are extending an existing 16-module tape-to-cloud migration tool and its 12-module DSPM sibling (the prior 11 turns of build context) with a new sibling project: a **SaaS License & Spend** tool — an MSP-ready seat-waste report for Microsoft 365, Slack, GitHub, Google Workspace, and a YAML-extensible catalog of other apps. Build it entirely from open-source components, with continuous forum-driven feature discovery, automatic PR approval for bot PRs, automatic conflict resolution, automatic issue fixing, and the 5-stage improvement loop. Primary engines: **Microsoft Graph SDK**, **Slack SDK**, **PyGithub**, plus optional Google Admin SDK. The 95/5 model discipline routes scaffolding to Grok Code Fast / Composer 2.5 Standard / `gemini-2.5-flash` (free tier) and reserves Claude Sonnet 5 / Opus 5 / Fable 5.1 for named hard triggers only. Total monthly cost: $0. This is a **spend report**, not an auto-revoker.

## 0. Read first

Before writing any code, read every file in `/workspace/mavis-deep-research/`. Then read, if present:

- `discovery/tape-to-cloud/cursor-prompt.md`
- `discovery/tape-to-cloud/continuous-improvement-loop-prompt.md`
- `discovery/dspm/cursor-prompt.md` and `dspm/README.md`
- `4-safe-builds-prompts/01-SSPM-CURSOR-PROMPT.md` (SSPM is posture; this product is **licenses/seats/money**)
- `forum-watcher/sources.yaml` and `forum-watcher/scripts/watch.py`
- `.cursor/rules/tape-to-cloud-build.mdc`

Do not re-implement tape-to-cloud, DSPM, SSPM, costreview, the forum-watcher, or the Bugbot replacement. Do not break `peter-evans/create-pull-request@v8` or `hmarr/auto-approve-action@v4`. Do **not** use `gautamkrishnar/keepalive-workflow`; keep cron alive with `licensespend/state/keepalive.txt`. SHA-pin every GitHub Action. Cron: Monday 09:00 AEST, `timezone: Australia/Sydney`.

Operator: 1-person AU MSP. Customers: AU SMBs over-buying M365 E3/E5, Slack Business+, GitHub seats. Output is a **draft reclaim pack for a human to approve**. Never revoke a license, deactivate a Slack seat, or remove a GitHub member unless `--apply` **and** `LICENSESPEND_APPLY=1` **and** the user id is in `allow-reclaim.txt`.

**PII / privacy:** store **seat metadata only** (user id hash, sku, assigned, last-active date, department if the directory already has it). Do not store mail, calendar bodies, Slack messages, GitHub issue text, or Drive files. Hash emails with a per-tenant salt before they hit DuckDB or HTML.

## 1. The 8-module architecture

Create a Python package `licensespend/` with exactly these 8 modules. Each: `cli.py` (Typer), `service.py`, `models.py` (Pydantic v2), `tests/`, `README.md` (≤ 200 words). JSON default; `--human` for a table. Fixture-first.

1. `licensespend/audit/` — tool + license inventory for this repo. CLI: `licensespend audit inventory`. **pip-audit + OSV.dev.**
2. `licensespend/m365/` — Microsoft Graph subscribed SKUs, user license assignments, last-signin. Wrap Graph as an optional extra; default path parses `examples/m365/subscribedSkus.json` + `examples/m365/users.json`. CLI: `licensespend m365 seats --fixture examples/m365/`. **Primary: `msgraph-sdk` + `azure-identity`. Scopes: `Organization.Read.All`, `User.Read.All`, `Directory.Read.All`, `AuditLog.Read.All` (sign-in activity). Read-only. Honest gap: Graph last-signin lags; treat >90d as unused, not "never".**
3. `licensespend/slack/` — billed active vs inactive members, guests, unused paid seats. Fixture: `examples/slack/users_list.json`. CLI: `licensespend slack seats --fixture examples/slack/`. **Primary: `slack-sdk` `users.list` + `team.info`. Do not call `conversations.history`. Honest gap: Slack Enterprise Grid org-level billing may need admin APIs not in the free test token — fixture covers it.**
4. `licensespend/github/` — org seats, outside collaborators, unused members (no contrib in N days via `examples/github/members.json` + `audit_log.json` fixtures). CLI: `licensespend github seats --org acme --fixture examples/github/`. **Primary: PyGithub (LGPL-3.0 — keep it a leaf dependency, do not copy source). Honest gap: contribution stats are incomplete without audit log; never clone private repos for this product.**
5. `licensespend/usage/` — join assigned vs last-active across M365/Slack/GitHub/(optional Google). DuckDB view `v_unused_seats` with `idle_days`, `sku`, `monthly_cost`. Price book YAML `licensespend/usage/pricebook.yaml` (AUD list prices the operator can edit; ship AU-typical defaults, not scraped vendor pages). CLI: `licensespend usage unused --idle-days 90`.
6. `licensespend/shadow/` — unapproved SaaS from SSO app catalogs, email DNS (SPF includes), expense CSV (`examples/shadow/expenses.csv` with vendor, amount, owner). CLI: `licensespend shadow scan`. **No CASB agent. Honest gap: DNS/expense heuristics only.**
7. `licensespend/renewals/` — contract calendar from `licensespend/renewals/contracts.yaml` (vendor, seats, renew_on, notice_days, amount_aud). CLI: `licensespend renewals upcoming --days 60`. ICS-optional export. Nudge copy is a **draft**.
8. `licensespend/report/` — **the product**. HTML + Markdown + JSON: seats bought vs used, reclaim $ (AUD), renewal 60-day list, shadow apps, SHA-256 watermark. CLI: `licensespend report build --client acme --out reports/`. Static HTML. Reclaim appendix lists **hashed** user ids + sku, not email, in the Free pack; Pro pack can include emails if `LICENSESPEND_INCLUDE_EMAIL=1` (still a local file, not uploaded).

A 9th module `licensespend/loop/` reuses the forum-watcher.

## 2. The `pyproject.toml`

```toml
[project]
name = "licensespend"
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
  "jinja2>=3.1.4",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-cov>=6.0.0",
  "ruff>=0.9.0",
  "mypy>=1.14.0",
  "pip-audit>=2.7.0",
]
m365 = ["msgraph-sdk", "azure-identity"]
slack = ["slack-sdk"]
github = ["PyGithub"]
google = ["google-api-python-client", "google-auth"]

[project.scripts]
licensespend = "licensespend.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Live SDKs are extras. Pytest uses fixtures only. Document required Graph app permissions in `licensespend/m365/README.md`.

## 3. The `docker-compose.yml` for local dev

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: licensespend
      POSTGRES_PASSWORD: licensespend
      POSTGRES_DB: licensespend
    ports: ["5435:5432"]
```

No MinIO. No message-queue. SQLite is an acceptable default store if you want zero Compose for `make licensespend-all`.

## 4. The GitHub Actions workflows

Prefix `licensespend-`. SHA-pin actions.

`licensespend-ci.yml` must fail if a report fixture contains a raw `@` email in `reports/` output unless `LICENSESPEND_INCLUDE_EMAIL=1` was set (it must not be set in CI):

```yaml
name: licensespend-ci
on:
  push:
    paths: ["licensespend/**", "examples/**", ".github/workflows/licensespend-*.yml"]
  pull_request:
    paths: ["licensespend/**", "examples/**", ".github/workflows/licensespend-*.yml"]
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      LICENSESPEND_INCLUDE_EMAIL: "0"
      LICENSESPEND_APPLY: "0"
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-groups
      - run: uv run ruff check licensespend tests
      - run: uv run pytest -q
      - run: uv run pip-audit --strict
      - uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: fs
          version: v0.71.2
          severity: HIGH,CRITICAL
          exit-code: "1"
```

- `licensespend-watch.yml` — Monday 09:00 AEST.
- `licensespend-auto-approve.yml` — bots only.
- `licensespend-rebase.yml` — bot rebase.
- `licensespend-monthly.yml` — `monthly/license-spend.md`.
- `licensespend-keepalive.yml` — `licensespend/state/keepalive.txt`.

Never commit `AZURE_CLIENT_SECRET`, Slack bot tokens, or GitHub PATs. `detect-secrets` / gitleaks in CI. GitHub 2026-03-25 auto-merge 422 caveat applies.

Pricebook shape (`licensespend/usage/pricebook.yaml`):

```yaml
currency: AUD
skus:
  - id: m365-e3
    vendor: microsoft365
    name: Microsoft 365 E3
    monthly_aud: 36.00
  - id: m365-e5
    vendor: microsoft365
    name: Microsoft 365 E5
    monthly_aud: 57.00
  - id: slack-business-plus
    vendor: slack
    name: Slack Business+
    monthly_aud: 15.00
  - id: github-team
    vendor: github
    name: GitHub Team
    monthly_aud: 4.00
```

Fixture users must include `assigned_sku`, `last_active` (ISO date or null), and `user_id` (opaque). Example:

```json
{
  "users": [
    {"user_id": "u-001", "sku": "m365-e3", "last_active": "2026-01-01", "department": "finance"},
    {"user_id": "u-002", "sku": "m365-e3", "last_active": "2026-08-20", "department": "ops"}
  ]
}
```

Makefile:

```makefile
licensespend-audit-inventory:
	python -m licensespend audit inventory
licensespend-all:
	python -m licensespend audit inventory
	python -m licensespend usage unused --idle-days 90 --fixture examples/
	python -m licensespend renewals upcoming --days 60
	python -m licensespend report build --client fixture --out reports/
```

`.cursor/rules/licensespend-build.mdc`: 8-module SaaS license & spend, Graph+Slack+PyGithub extras, metadata-only, no revoke without dual gates.

## 5. The 4-stage build order — commit as you go

**Stage 1 — scaffold.** Package, audit, schema, `examples/m365/*.json`, `examples/slack/*.json`, `examples/github/*.json`, pricebook YAML, CI. Check: `make licensespend-audit-inventory`.

**Stage 2 — m365 + slack + github parsers.** Golden tests: 12 assigned E3, 3 unused >90d, 2 Slack guests, 1 GitHub outside collaborator. Check: `licensespend usage unused --idle-days 90 --fixture examples/`.

**Stage 3 — shadow + renewals.** Expense CSV + contracts YAML. Check: `licensespend renewals upcoming --days 60` returns a known vendor.

**Stage 4 — report + loop + optional live extras.** HTML+MD+JSON with SHA-256. Emails hashed unless flag set. Check: `make licensespend-all`.

## 6. The forum-watcher sources extension

```yaml
- name: r/msp
  url: https://www.reddit.com/r/msp/.rss
  module_hint: licensespend/report, licensespend/m365
  max_items: 25
- name: r/sysadmin
  url: https://www.reddit.com/r/sysadmin/.rss
  module_hint: licensespend/usage, licensespend/shadow
  max_items: 25
- name: r/PowerShell
  url: https://www.reddit.com/r/PowerShell/.rss
  module_hint: licensespend/m365
  max_items: 15
- name: msgraph-releases
  url: https://github.com/microsoftgraph/msgraph-sdk-python/releases.atom
  module_hint: licensespend/m365
  max_items: 10
- name: slack-sdk-releases
  url: https://github.com/slackapi/python-slack-sdk/releases.atom
  module_hint: licensespend/slack
  max_items: 10
- name: pygithub-releases
  url: https://github.com/PyGithub/PyGithub/releases.atom
  module_hint: licensespend/github
  max_items: 10
```

HN: `saas sprawl`, `microsoft 365 unused licenses`, `slack billed seats`. Skip Zylo/Productiv/Torii commercial Evaluate hits.

## 7. The free-LLM classification prompt

Gemini Flash. Input: sku name + idle_days + **hashed** user id. No raw email.

```json
{
  "finding_id": "string",
  "client_summary": "string, <= 40 words",
  "reclaim_aud": "number",
  "confidence": "low|medium|high",
  "human_action": "draft email to manager, do not revoke"
}
```

Abstain if sku unknown in pricebook.

## 8. The auto-PR / conflict / issue-fix patterns

Bot-only auto-approve. Rebase-only. `good first issue` only. Do not auto-fix Graph permission changes or pricebook AUD amounts (operator-owned).

## 9. The 5-stage loop wiring

Discover = watcher + SDK releases. Evaluate ≥ 7. Integrate Monday. Validate pytest (hash emails in report tests). Compound = monthly unused-seat $ trend.

## 10. The cost ceiling

$0/month. Graph/Slack/GitHub are customer tenants. No Zylo, no Productiv, no Microsoft 365 Copilot requirement, no Slack Analytics paid plan requirement (fixtures cover analytics-shaped JSON).

## 11. The eight hard rules

1. No paid SaaS-management platforms.
2. No GPU/Ollama.
3. Do not break PR handoff.
4. Trivy 0.71.2 / 0.70+ (CVE-2026-33634).
5. Metadata-only: no mail/Slack/GitHub content.
6. No license revoke without `--apply` + `LICENSESPEND_APPLY=1` + allow-list.
7. Dedupe Discover by SHA-256 URL.
8. In-repo keepalive.

Plus: hash emails by default; PyGithub stays a dependency (LGPL-3.0) not vendored source; SHA-pin Actions; pricebook is operator-edited AUD, not a crawler.

## 12. The completion criteria

Four stages committed. `make licensespend-all` on fixtures. Report watermark verifies. Tests prove unused-seat math and email hashing. Watch + bot auto-approve present. `.cursor/rules/licensespend-build.mdc` present. Live Graph is optional.

## 13. The anti-patterns to avoid

- Do not use Sonnet/Opus for scaffolding.
- Do not store Slack messages or mailbox content (that is DSPM/SSPM-adjacent and out of scope).
- Do not auto-reclaim seats.
- Do not scrape vendor price pages.
- Do not commit secrets.
- Do not auto-approve human PRs.
- Do not require Enterprise Grid / Entra P2 / GitHub Enterprise extras for the fixture path.
- Do not send unhashed emails to an LLM.
- Do not reimplement cnspec posture scans; if you need MFA/sharing, call out SSPM as the sibling.

## 14. The single takeaway

**Graph + Slack SDK + PyGithub inventory the seats, DuckDB finds idle, Jinja writes the reclaim pack.** It is not Zylo. Honest gap: ~40-60% of commercial SaaS management (no procurement workflow, no auto-SSO discovery, no contract PDF OCR). At $0/month it is the right quarterly license-review for AU SMBs. Paste this whole message into Composer, set Max, scaffold `licensespend/`, commit as you go.

[model used: Composer/Grok] [Bucket: B] [module: licensespend]
```

---

## 4. DMARC + Email Deliverability

Source file: `04-DMARC-DELIVERABILITY-CURSOR-PROMPT.md` — paste the block as a new Composer message.

```
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
```

---

## References

[1] Mondoo cnspec — open-source policy-as-code scanner (SaaS, cloud, endpoints). https://github.com/mondoohq/cnspec

[2] Scan SaaS platforms with cnspec (M365, Google Workspace, GitHub, Slack, Okta). https://mondoo.com/docs/cnspec/saas/overview

[3] Mondoo Microsoft 365 Security policy bundle. https://mondoo.com/docs/cnspec/saas/m365

[4] Mondoo GitHub Security policy bundle. https://mondoo.com/docs/cnspec/saas/github

[5] Prowler — open-source CSPM (Apache-2.0). https://github.com/prowler-cloud/prowler

[6] Steampipe — SQL over cloud APIs (AGPL-3.0). Use as CLI subprocess only. https://github.com/turbot/steampipe

[7] Cloud Custodian — policy-as-code for cost, tags, and guardrails (Apache-2.0). https://github.com/cloud-custodian/cloud-custodian

[8] Cloud Custodian EBS unattached garbage-collection example (mark-for-op). https://www.cloudcustodian.io/docs/aws/examples/ebsgarbagecollect.html

[9] Microsoft Graph SDK for Python. https://github.com/microsoftgraph/msgraph-sdk-python

[10] Slack SDK for Python. https://github.com/slackapi/python-slack-sdk

[11] PyGithub — GitHub API v3 (LGPL-3.0; depend, do not vendor). https://github.com/PyGithub/PyGithub

[12] parsedmarc — parse DMARC aggregate, failure, and TLS-RPT reports. https://github.com/domainaware/parsedmarc

[13] parsedmarc on PyPI. https://pypi.org/project/parsedmarc/

[14] dnspython — DNS toolkit. https://github.com/rthalley/dnspython

[15] RFC 7489 / RFC 9989 — DMARC. https://www.rfc-editor.org/rfc/rfc7489

[16] RFC 8460 — SMTP TLS Reporting. https://www.rfc-editor.org/rfc/rfc8460

[17] MTA-STS (RFC 8461) policy file at `https://mta-sts.<domain>/.well-known/mta-sts.txt`.

[18] DuckDB — in-process analytics. https://github.com/duckdb/duckdb

[19] Gemini Developer API free-tier limits. https://ai.google.dev/gemini-api/docs/pricing

[20] GitHub Actions timezone support for scheduled workflows (2026-03-19). https://github.blog/changelog/2026-03-19-github-actions-late-march-2026-updates/

[21] GitHub auto-merge 2026-03-25 behavior change (HTTP 422 unless required checks exist). https://github.com/orgs/community/discussions/190610

[22] peter-evans/create-pull-request v8. https://github.com/peter-evans/create-pull-request

[23] hmarr/auto-approve-action v4. https://github.com/hmarr/auto-approve-action

[24] Trivy supply-chain incident 2026-03-19 (CVE-2026-33634, malicious v0.69.4); pin v0.70+ / v0.71.2.

[25] MinIO Community Edition archived 2026-04-25 — do not add as S3 for these builds. Prefer fixtures or customer cloud.

[26] DSPM sibling (this repo) — 12-module Cyera-like OSS build, Steampipe CLI-only, $0/month. `discovery/dspm/` and `dspm/` on feature branches.

[27] Tape-to-cloud Cursor prompt (95/5 routing, 16 modules). `discovery/tape-to-cloud/cursor-prompt.md`

[28] Forum-watcher + 5-stage loop. `forum-watcher/` and `discovery/tape-to-cloud/continuous-improvement-loop-prompt.md`

## Single takeaway

Four paste-ready Composer prompts. Each scaffolds a fixture-first Python CLI report pack, reuses the DSPM loop, and stays at $0/month. Paste one file per new repo. Do not paste this master file — it has framing headings and fences around the prompts on purpose.
