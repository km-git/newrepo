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
