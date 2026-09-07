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
