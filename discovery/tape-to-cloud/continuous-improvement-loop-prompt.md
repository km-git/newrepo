# Cursor Prompt: Tape-to-Cloud Tool — Free-Tier Self-Sustaining Improvement Loop

You are working on the **tape-to-cloud migration tool** (16 modules: audit, analytics, vtl-cloud, restore, disk-ingest, email-extract, email-migrate, tape-duplicate, media-ingest, tape-ops, tape-saas, tape-vault, destroy, llm-corpus, ml-enrich, monetize). Every change you make must pass through the **5-stage loop** (discover → evaluate → integrate → verify → release) and must use the **free tier** of every tool. Never suggest a paid SaaS, a paid Cursor plan upgrade, an Ollama install, or a self-hosted GPU. If a task seems to require paid tooling, find a free alternative or split the task into parts that fit the free tier.

## Model routing — 95% cheap / 5% expensive

Bucket A (95% of work — pick in this order):
- Grok Code Fast 1, Grok 4.5, GPT-5.6 Luna, Claude Haiku 4.5

Bucket B (5% of work — only when Bucket A is wrong or the task matches the trigger):
- Composer 2.5 Standard

Bucket C (reserved, ≤1% — only on explicit user request):
- Claude Sonnet 5, Claude Opus 5, Claude Fable 5.1

Triggers that force Bucket B/C:
- Reading a vendor-specific format (Veeam MTF, TSM DB schema, GroupWise PST, NetBackup catalog, Cohesity view manifest)
- Touching the Snowball / Tape Gateway state machine
- Working on the WORM / NIST 800-88 purge policy
- Designing the Temporal workflow for restore-at-scale
- The Nexus data model and chain-of-custody posture

## Hard rules

1. **No Bugbot.** Bugbot is dead in this repo. The replacement is the `prek` + `Ruff` + `zizmor` + `OSV-Scanner` + `actionlint` stack in CI. If you find yourself wanting a comment-only review tool, write a `pre-commit` hook instead. If Cursor reports a Bugbot usage cap, do not retry — fall through to Ruff locally and the CI checks on the PR.
2. **No paid Cursor plan features.** No Background Agents, no Bugbot Pro, no Max Mode. Stay on the free tier.
3. **Every code change must compile + lint + test on the first try.** Run `uv run ruff check --fix .` and `uv run ruff format .` locally before declaring done. If a CI workflow is the change, run `prek run --all-files` to catch `zizmor` and `actionlint` issues.
4. **SHA-pin every new GitHub Action.** Use the format `uses: owner/action@<commit-sha>  # vX.Y.Z`. Dependabot for the `github-actions` ecosystem will roll the SHAs.
5. **Conventional Commits for every commit.** `feat:`, `fix:`, `chore(deps):`, `feat!:` for breaking. The CHANGELOG is auto-generated from these.
6. **`uv` for all Python dependency work.** `uv add`, `uv add --dev`, `uv lock`, `uv sync`, `uv run`. Never edit `pyproject.toml` dependencies by hand.
7. **`uv run ruff check` is the pre-commit gate.** If it fails, fix it. Do not silence rules unless the suppression is in the commit message and the rule is genuinely wrong.
8. **One PR = one concern.** If a refactor surfaces a Bugbot-equivalent issue, do not bundle the fix into the same PR. Open a follow-up.
9. **Free-tier only.** No Snyk, no Sonatype, no Datadog, no Sentry cloud, no Bugbot Pro. OSV.dev is free and key-less; use it. GlitchTip self-host is free; use it for the error layer when needed. SigNoz self-host is free; use it for traces when needed.
10. **No silent retries on rate caps.** If Dependabot or Renovate rate-limits you, document it in the PR description and switch to the documented fallback (Dependabot → Renovate, Mend-hosted → self-host). Do not loop trying the same tool.

## Default command sequence for any task

Before opening a Cursor Composer session for a code change:

```bash
git pull --rebase origin main
uv sync --all-groups
uv run prek run --all-files   # catches ruff + zizmor + actionlint locally
uv run pytest -q
```

After the change, before declaring done:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run prek run --all-files
uv run pytest -q
git status   # confirm only intended files changed
```

For workflow YAML changes (anything in `.github/workflows/`), the sequence is the same plus a `prek` step that runs `zizmor` and `actionlint` against the changed file.

## Module-to-tool hints (use these when the task maps to a module)

| Module | First look at | Avoid |
|---|---|---|
| `audit` | OSV-Scanner output on the manifest reader; `mt-st` + `stenc` for tape control | Any tool that hides the tape header bytes |
| `analytics` | DuckDB (free, embedded) for OLAP; Polars for in-process | Pandas on >1M rows without a column store |
| `vtl-cloud` | `ltfs` (HP/IBM) + Syft for the migration container SBOM | Any vendor lock-in to a single cloud |
| `restore` | OSV.dev to verify lib versions before shipping a restore bundle | Restoring to a different vendor's backup app blindly |
| `disk-ingest` | Syft for the ingest tool SBOM; Ruff for the pipeline code | NAS mounts that bypass the manifest reader |
| `email-extract` | OSV-Scanner on `libpff-python`, `extract-msg`; Renovate for `extract-msg` updates | Custom PST parsers when a maintained one exists |
| `email-migrate` | Dependabot for the Graph SDK; OSV.dev on Graph SDK version | Hard-coded Graph endpoints (use the SDK) |
| `tape-duplicate` | `actionlint` + `zizmor` to keep the orchestration workflow safe | `shell=True` in any orchestration code |
| `media-ingest` | Trivy for the FFmpeg container; cosign for the output MP4 hash | Unverified codec versions |
| `tape-ops` | Ruff + `zizmor` for the `mt` shell-out paths; `actionlint` shellcheck | `os.system()` calls |
| `tape-saas` | OSV-Scanner on the SaaS dependencies; SigNoz for observability | Sentry cloud |
| `tape-vault` | `uv` lockfile + Syft for the vault-side tool; Renovate for lifecycle scripts | Manual lifecycle policies (use S3 Object Lock or equivalent) |
| `destroy` | cosign for the destruction certificate; `cosign verify-blob` for the audit trail | Software-only wipe verification (needs NIST 800-88 hardware attestation) |
| `llm-corpus` | Model feed watcher + `releases.atom`; OSV-Scanner on `litellm`, `instructor` | Pinning a model version that is more than 90 days old |
| `ml-enrich` | OSV-Scanner on `torch`, `transformers`; cosign for the enrichment output; `uv` lockfile for the ML versions | Floating ML versions across corpus runs |
| `monetize` | OSV-Scanner on the billing libs; GlitchTip for usage events; Renovate for the Stripe SDK | Hard-coded API keys in the repo |

## Free-tier tool index (paste into the PR description if asked "why this stack")

- **Dependabot** — security + version updates, GitHub-native, free
- **Renovate** (`config:best-practices` preset) — grouped minor/patch updates + SHA-pinning, Mend-hosted free tier is 1-concurrent-job/4-hr cycle, self-host (AGPL-3.0) if you exceed
- **`release-please-action`** (`googleapis/release-please-action@v4`) — Conventional Commits → release PR → GitHub Release, free
- **`anchore/sbom-action`** — Syft-based SBOM in CycloneDX JSON, free
- **`sigstore/cosign-installer`** — keyless signing via GitHub OIDC, free
- **`google/osv-scanner-action`** — OSV.dev CVE scan, SARIF upload to Security tab, free
- **`zizmorcore/zizmor-action`** — GitHub Actions security scanner, free
- **`j178/prek-action`** — Rust-rewrite of pre-commit, 10× faster, free
- **`astral-sh/setup-uv`** + `Ruff` — Python linter + formatter, free, part of `uv 0.10+`
- **`rhysd/actionlint`** — workflow YAML linter with shellcheck integration, free
- **OSV.dev API** — `https://api.osv.dev/v1/query`, key-less, no rate cap, free
- **Track Awesome List** — `https://www.trackawesomelist.com/`, RSS feed of 500+ awesome-list diffs, free
- **GitHub `/releases.atom`** — `https://github.com/<owner>/<repo>/releases.atom`, Atom feed of every release, free
- **GlitchTip** (Phase 2, optional) — BSD, Sentry-SDK-compatible via DSN swap, self-host on 512MB VPS
- **SigNoz** (Phase 2, optional) — Apache 2.0, OpenTelemetry-native, ClickHouse-backed

## When the user asks for a paid tool

Default response:

> That tool is paid. The free-tier equivalent is `<X>`. Want me to scaffold `<X>` instead? If you have a specific reason `<X>` is the right call (compliance, scale, SLA), tell me and I'll plan around it, but the default build will not assume paid tooling.

## When the user asks for self-hosted GPU / Ollama

Default response:

> Out of scope for this tool. The 95/5 routing uses hosted cheap models for Bucket A (Grok Code Fast, Grok 4.5, GPT-5.6 Luna, Claude Haiku 4.5) and Bucket B (Composer 2.5 Standard) for the long tail. If a specific task genuinely needs a local model, name the task and we'll see if a hosted equivalent covers it.

## Monday 9 AM AEST review checklist (if asked "what should I do today?")

1. Open the Dependabot dashboard issue. Review queued PRs.
2. Open the Renovate Dependency Dashboard. Approve the batched minor/patch PR.
3. Check the Security tab for OSV-Scanner / Dependabot alerts. Critical = today, High = this week.
4. Read the model feed watcher logs. Any new SDK release? Bump the pin if yes.
5. Scan Track Awesome List RSS for the 3 lists that match the 16 modules. Add candidates to the eval queue.
6. Glance at the latest GitHub Release. Is the CHANGELOG accurate? Fix commit messages if not.

Budget: 15 minutes when the loop is healthy, 30-60 when something needs human eyes, never more than 90.

## Failure modes and recovery (if the build is broken)

- **Cursor hits a usage cap** → do not retry. Fall through to local `prek` + `uv run ruff check` + the CI checks on the next PR.
- **Ruff is too slow on a giant file** → run `uv run ruff check path/to/file.py` instead of `.` to scope it. Still free, still 100× faster than flake8.
- **OSV-Scanner finds a CVE in a transitive dep** → open a PR with the bump + a CHANGELOG note. Do not silently upgrade; the PR is the audit trail.
- **Dependabot auto-merge fired on a bad update** → `git revert` the merge commit, add the package to `packageRules[].matchPackageNames` in `renovate.json` with `enabled: false`, and open an issue tagged `tooling:rollback`.
- **A new model invalidates the LLM cache** → bump the pin in `llm-corpus` and `ml-enrich`, re-run those modules, attach the new signed SBOM to the release.

## The single rule

If a change does not pass `uv run prek run --all-files` + `uv run pytest -q` locally, it is not done. If a change to `.github/workflows/` does not pass `prek` (zizmor + actionlint), it is not done. If a release does not have a signed SBOM, it is not shipped. If a tool costs money and the question didn't explicitly say "spend money", use the free alternative.
