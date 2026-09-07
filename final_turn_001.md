# Cursor Prompt: Build the Tape-to-Cloud Migration Tool

A copy-paste-ready Cursor prompt for building the tape-to-cloud migration tool described in the blueprint. It combines two things: the **95/5 model routing discipline** (Grok Code Fast / Grok 4.5 / Composer 2.5 Standard for ~95% of work, Claude Sonnet 5 / Opus 5 / Fable 5.1 for the ~5% that genuinely need frontier reasoning) and the **project-specific build instructions** for this exact tool — the source/target matrix, the integrity/chain-of-custody requirements, the orchestration choices, the menu-to-module map.

Two artifacts below: a **Project Rule** (`.mdc`) you drop into the repo's `.cursor/rules/` directory, and a **Global User Rule** you paste into Cursor → Settings → Rules. Plus the one-time settings checklist and the 30-day audit loop from the generic prompt, reused because the 95/5 mechanism is the same.

The model names and prices match Cursor's September 2026 lineup: Grok Code Fast (free), Grok 4.5 ($2/$6), Composer 2.5 Standard ($0.5/$2.5), Claude Haiku 4.5 ($1/$5), GPT-5.6 Luna ($0.2/$1.2) on the cheap side; Claude Sonnet 5 ($2/$10), Claude Opus 5 ($5/$25), Claude Fable 5.1 ($10/$50) on the expensive side. Verify against the live picker when installing — pricing drifts.

---

## 1. The Principle for This Project

The tool in the blueprint is a controller + worker system with three design constraints: source-agnostic (LTO-1 through LTO-10, DLT/AIT/DDS, VTL, TSM/NetBackup/BackupExec/NetWorker/ARCserve/Data Protector/CommVault/Veeam), target-agnostic (any S3-compatible endpoint), and use-case-complete (every line of the Iron Mountain-style service menu maps to a first-class module). The engineering concentrates in three places: the format-specific readers, the integrity/audit layer, and the orchestration that survives weeks-to-months runs.

The 95/5 split applies as follows. **Bucket A (cheap floor) and Bucket B (Composer 2.5 Standard as the workhorse) cover ~95% of coding work**: scaffolding the controller/worker skeleton, writing the S3-compatible SDK adapters, implementing `audit`, `analytics`, `disk-ingest`, `tape-duplicate`, `tape-ops`, `tape-vault`, `monetize`, the SHA-256 manifest writer, the Postgres audit schema, the S3 multipart uploader, the lifecycle policy sweep, `ffmpeg` proxies, `tesseract` OCR, PII scrubbing, tokenization sharding. **Bucket C/D (expensive models) cover the ~5% that genuinely need frontier reasoning**: the format-specific parsers for TSM/NetBackup/BackupExec headers, the AWS Snowball + Tape Gateway OpsHub state machine, the WORM-anchor policy logic, the Multi-tape-state Temporal workflow design, the GroupWise-Post-Office-to-O365 extractor, the chain-of-custody legal posture, the decision on whether to license MediaGenie Proteus vs re-implement, and the multi-tenant Nexus portal architecture.

---

## 2. The Model Tier List (September 2026)

| Bucket | Models | Price (in/out per M tokens) | When to use here |
|---|---|---|---|
| **A — Cheap floor** | Grok Code Fast · Grok 4.5 · GPT-5.6 Luna · Claude Haiku 4.5 | $0.2–$2 / $1.2–$6 | Default for everything. Repo search, type fixes, docstrings, lint, scaffolding, simple test generation, README, comments |
| **B — Cheap flagship** | Composer 2.5 Standard | $0.5 / $2.5 | Sustained agent loops, multi-file refactors, migration scripts. Standard is 6× cheaper than Fast for the same model weights |
| **C — Expensive flagship** | Composer 2.5 Fast · Claude Sonnet 5 · GPT-5.6 Sol · GPT-5.6 Terra · Gemini 3.1 Pro | $2–$4 / $10–$20 | Format-specific parsers, Multi-step Temporal workflow design, Snowball/Tape Gateway state machine, KMS envelope encryption logic |
| **D — Frontier (≤5%)** | Claude Opus 5 · Claude Fable 5.1 | $5–$10 / $25–$50 | Architecture decisions only: license-vs-re-implement MediaGenie Proteus, Nexus multi-tenant data model, chain-of-custody legal posture, irreversible migration path review |

---

## 3. Artifact A — Project Rule (`.cursor/rules/tape-to-cloud-build.mdc`)

Save as `.cursor/rules/tape-to-cloud-build.mdc` at the repo root. `Apply Intelligently` means Cursor's agent reads the description and pulls the rule in whenever the chat looks like work on this tool [1][2].

```markdown
---
description: Build the tape-to-cloud migration tool from the blueprint. Route 95% of work to Grok Code Fast / Grok 4.5 / Composer 2.5 Standard / Claude Haiku 4.5 / GPT-5.6 Luna; reserve Claude Sonnet 5 / Opus 5 / Fable 5.1 for ~5% hard triggers. Source-agnostic, target-agnostic, audit-first. Max Mode off.
globs:
alwaysApply: false
---

# Tape-to-Cloud Build Rule (95/5 routing)

You are helping build a vendor-agnostic tape-to-cloud migration tool. Three constraints govern every decision:

1. **Source-agnostic.** Handle LTO-1 through LTO-10, DLT/AIT/DDS/VXA, VTL, and proprietary backup-app formats (TSM, NetBackup, Backup Exec, ARCserve, NetWorker, Data Protector, CommVault, Veeam MTF, Catalogic DPX). NetBackup cannot read TSM tapes directly; the tool needs its own format-aware read/catalog layer.
2. **Target-agnostic.** Same code path writes to AWS S3/Glacier/Deep Archive, Azure Blob (Hot/Cool/Archive), Google Cloud Storage, Backblaze B2, Wasabi, Cloudian, SeaweedFS, Ceph. Use any S3-compatible SDK; do not hard-code to one cloud. MinIO Community Edition is archived (GitHub: April 25, 2026); do not recommend it as the self-hosted S3 layer.
3. **Use-case-complete.** Every menu line below must be expressible as a first-class module on the same core.

## Menu → module map (the 16 first-class modules)

When asked to implement a feature, locate it here first and reuse the same core:

| Menu item | Module | Concrete deliverable |
|---|---|---|
| Comprehensive Media Audit | `audit` | Per-tape JSON: barcode, format, byte count, header hash, file list |
| Archive Insight | `analytics` | SQL/indexed view over audit data: age distribution, duplicate detection, PII flagging |
| Tape Migration: Virtualization | `vtl-cloud` | AWS Tape Gateway / StarWind deployment + lifecycle policy |
| Tape Migration: Restore | `restore` | On-demand read from cloud → staging → courier/network return |
| Disk-Based Data Ingest | `disk-ingest` | USB/NAS reader, S3 sync, manifest generation |
| Email Restore From Tape | `email-extract` | GroupWise, Lotus, Notes, Exchange, PST extractors as plugins |
| GroupWise to M365 | `email-migrate` | GroupWise Post Office parse + O365 import (Graph API or PST) |
| Tape Copy and Duplication | `tape-duplicate` | 1-to-N hardware duplication, hash verification, signed manifests |
| Video Digitization | `media-ingest` | LTO → staging → proxy/transcode → S3 + Media2Cloud enrichment |
| Legacy Tape Management | `tape-ops` | Barcode tracking, drive/library health, scheduled audit |
| Cloud-based Legacy Tape Mgmt (Nexus) | `tape-saas` | Tenant-isolated VTL, restore portal, immutable catalog |
| Tape Storage | `tape-vault` | Integration with offsite-vault APIs for residual physical tape |
| Media Destruction | `destroy` | NIST 800-88 + IRS Pub 1075 certificate generation |
| Legacy Data for LLM | `llm-corpus` | Extract → dedup → PII-scrub → tokenize → training format |
| AI and ML Services | `ml-enrich` | Rekognition / Transcribe / Comprehend / Textract pipeline |
| Monetization Strategy | `monetize` | License tagging, access control, royalty reporting |

## Default model selection (95%)

For routine work on this repo, use a **Bucket A** model:

1. **Grok Code Fast** — free, fastest for repo search, small edits, type fixes, lint.
2. **Grok 4.5** — slightly more nuanced reasoning, still cheap ($2/$6 per M tokens).
3. **Composer 2.5 Standard** (not Fast) — for sustained agent work, multi-file refactors, migration scripts. Standard is 6× cheaper than Fast for the same weights.
4. **GPT-5.6 Luna** — only when a Claude-family model has been failing.
5. **Claude Haiku 4.5** — last resort in Bucket A; still cheap.

For long agent loops, the `audit`, `disk-ingest`, `tape-vault`, `monetize`, `analytics`, and `llm-corpus` modules are Bucket A/B by default.

## Escalate to Bucket C / D (the 5%)

Escalate to an expensive model **only** when at least one of these is true:

- The change is a **multi-file refactor with cross-cutting effects** across the 16 modules (e.g., refactoring the manifest schema affects `audit`, `analytics`, `tape-ops`, `tape-saas`).
- The bug is **subtle concurrency, distributed-systems, or security-sensitive** (auth on the restore portal, KMS envelope key handling, manifest signature, WORM retention lock, Temporal workflow replay safety, AWS credential scope).
- The user is **making an architecture decision**: license vs re-implement MediaGenie Proteus for TSM/NetBackup/BackupExec readers; Temporal vs Airflow vs Argo for the orchestrator; multi-tenant data model for `tape-saas`; chain-of-custody legal posture.
- The task requires **long-context reasoning over >50K tokens** of code at once (e.g., the full module map, the full integrity layer, the full target-cloud matrix).
- A Bucket A model has already failed on this same task in the same chat, and you can name the specific failure (e.g., a wrong TSM header parser, a wrong AWS Snowball OpsHub step, a wrong S3 Glacier retrieval tier).

For every escalation, state in the response *why* you escalated and which trigger fired. Do not escalate silently.

The 5% is concentrated in these specific areas of this tool:
- **Format-specific readers for proprietary backup-app formats** (TSM, NetBackup, Backup Exec, ARCserve, NetWorker, Data Protector, CommVault, Veeam MTF) — the headers are undocumented and require careful reverse-engineering reasoning.
- **AWS Snowball + Tape Gateway state machine** — the OpsHub-driven workflow, KMS key selection, manifest format, virtual-tape status transitions are subtle.
- **WORM-anchor policy logic** — S3 Object Lock Compliance mode, GCS Bucket Lock, Azure Immutable Blob; the legal posture and key-deletion semantics.
- **Temporal workflow design** — activity timeouts, retry policies, signal handling, durable execution semantics.
- **Multi-tenant Nexus portal data model** — tenant isolation, restore-permission graph, immutable catalog.
- **Chain-of-custody legal posture** — what the certificate must say for IRS Pub 1075, FISMA, HIPAA, GDPR.

## Hard "never escalate" list

Do **not** use Bucket C or D for any of these, even if asked:

- Writing docstrings, comments, README, ADRs, or type annotations.
- Renaming variables, reformatting, fixing lint warnings.
- Generating unit tests for already-written code.
- Scaffolding the controller/worker skeleton, the S3 SDK adapter, the SHA-256 manifest writer, the multipart uploader, the lifecycle policy sweep, the `ffmpeg` proxy pipeline, the `tesseract` OCR call, the PII scrubber, the tokenization sharder, the Postgres audit schema, the `disk-ingest` reader, the `tape-vault` API integration, the `monetize` license-tag writer.
- Translating between obvious equivalents (e.g., boto3 vs azure-storage-blob — pick one, the other is a Bucket A port).
- Searching the repo, explaining a file, summarizing the blueprint.

## Tech-stack defaults

When the task is to scaffold, default to this stack unless the user says otherwise:

- **Language**: Python 3.12+ (best library coverage for tape I/O, ML, and cloud SDKs).
- **Tape I/O**: `mt-st` for control, `mbuffer` for streaming buffer, `tar` or `ltfs` for read, `stenc` for hardware-decryption of AIT.
- **Hashing**: `hashlib` SHA-256, with `xxhash` for fast non-cryptographic checksums on dedup.
- **Cloud SDK**: `boto3` for AWS, `azure-storage-blob` for Azure, `google-cloud-storage` for GCP, all S3-compatible.
- **Catalog DB**: Postgres + SQLAlchemy 2.x + Alembic.
- **Orchestrator**: Temporal (per-tape state machine) + Argo (parallel bursts) + Airflow (daily catalog refresh). Default to Temporal for new code.
- **Backup-format readers**: license MediaGenie Proteus or implement custom; do not invent a half-working TSM/NetBackup parser on a cheap model.
- **Video**: `mediainfo` for metadata, `ffmpeg` for proxies, AWS Media2Cloud reference pipeline.
- **Email**: Transend Migrator (or equivalent) for GroupWise-to-O365.
- **AI/LLM**: `tesseract`, `pdftotext`, `presidio` for PII, `datatrove` or `dolma` for tokenization.

## Context discipline (the silent cost killer)

Cheap models get expensive when you feed them 200K tokens of unrelated files. Before every call:

- Use `@file` and `@folder` references instead of pasting code blocks.
- Never use `@codebase` unless the question genuinely spans the repo.
- For the 16-module map, the integrity layer, and the target-cloud matrix, point to the relevant section of the blueprint by filename, not by full paste.
- Add a short "what matters" note before the code: the entry point, the failing behavior, the constraints, the exact files expected to change.
- Maintain an ignore list: `node_modules/`, `.venv/`, `dist/`, `build/`, `__pycache__/`, `*.pyc`, `tests/fixtures/large_*.bin`, `vendor/`, `coverage/`.
- Start fresh conversations when the context gets bloated.

## Max Mode

Max Mode is **off by default**. Do not turn it on unless the user explicitly approves it for the current task. Max Mode expands context to the model's full window and bills proportionally. It is the single most common budget blow-up.

For thinking-mode models (GPT-5.4, Opus 4.5/4.6, Sonnet 4.5/4.6), Max Mode is currently selected by default when you pick the model, and there are reports it cannot be toggled off. If you find yourself in this state, switch off the thinking-mode model and use a non-thinking cheap model instead.

## Self-report at the end of every multi-step task

When the work is done, append a one-line note:

`[model used: <name>] [Bucket: A/B/C/D] [reason if Bucket C/D: <trigger>]` `[module: <audit|analytics|vtl-cloud|restore|...>]`

This makes the 95/5 split auditable in chat history and ties each model call to a specific module.

## When the user explicitly asks for a specific model

If the user names a model in their request (e.g., "use Opus 5 to design the Nexus multi-tenant data model"), use that model. Do not silently re-route to a cheaper one. The user is paying attention; respect their override.

## Stop conditions

Stop and ask the user before:

- Adding a new third-party dependency that has a per-token or per-GB cost (e.g., a new SaaS API).
- Choosing between license-and-wrap vs re-implement for any proprietary backup format.
- Committing to a specific cloud vendor for the default target.
- Any change to the chain-of-custody manifest schema (legal exposure).
- Any change to the WORM retention policy (regulatory exposure).
```

---

## 4. Artifact B — Global User Rule (Settings → Rules)

For users who want the 95/5 discipline everywhere (not just inside this repo). Open **Cursor → Settings → Rules → User Rules** and paste the following. This is the global, always-on equivalent of the project rule.

```
ROUTING DISCIPLINE (apply to every chat and agent run, especially when
building the tape-to-cloud migration tool from the blueprint)

Default model: pick a cheap one. Use Grok Code Fast first, then Grok 4.5,
then Composer 2.5 Standard (not Fast), then GPT-5.6 Luna, then
Claude Haiku 4.5. Never start a chat on Sonnet, Opus, Fable, or
Composer Fast unless I asked for it by name.

Escalate to an expensive model (Sonnet 5, Opus 5, Fable 5.1,
Composer Fast, GPT-5.6 Sol/Terra) only when:
  - the change is a multi-file refactor with cross-cutting effects
    across the 16 modules of the tape-to-cloud tool,
  - the bug is subtle concurrency / security / KMS / WORM / Temporal
    replay / AWS credential scope,
  - I am making an architecture decision (license vs re-implement
    MediaGenie Proteus, orchestrator choice, multi-tenant data model,
    chain-of-custody legal posture),
  - the task needs >50K tokens of code at once, or
  - a cheap model has already failed on the same task in this chat
    and you can name the specific failure.
Tell me which trigger fired when you escalate.

The expensive models are NOT for: docstrings, comments, README, ADR
drafts, renames, lint fixes, scaffolding, test generation for
already-written code, repo search, code explanation, the SHA-256
manifest writer, the S3 multipart uploader, the lifecycle policy
sweep, the Postgres audit schema, the ffmpeg proxy pipeline, the
tesseract OCR call, the PII scrubber, the tokenization sharder, the
disk-ingest reader, the tape-vault API integration, or the monetize
license-tag writer.

Default tech stack for this project:
- Python 3.12+
- mt-st, mbuffer, tar, ltfs, stenc for tape I/O
- boto3 (S3-compatible) for cloud SDKs
- Postgres + SQLAlchemy 2.x for the audit DB
- Temporal (per-tape state machine), Argo (bursts), Airflow (daily refresh)
- License MediaGenie Proteus for proprietary backup-app formats unless I say otherwise
- mediainfo, ffmpeg, tesseract, presidio, datatrove for media/AI

Keep context small. Use @file / @folder, not @codebase. Point to the
blueprint section by filename, not by full paste. Start fresh chats
when context bloats. Ignore node_modules, .venv, dist, build,
__pycache__, large fixtures, vendor, coverage.

Max Mode is OFF by default. Do not enable it unless I say so.

At the end of multi-step tasks, write one line:
[model: <name>] [Bucket: A=cheap / B=cheap-flagship / C=expensive / D=frontier]
[reason if B/C/D: <trigger>] [module: <audit|analytics|vtl-cloud|...>]

Stop and ask me before: adding a per-token SaaS dependency, choosing
license-vs-reimplement, picking a default cloud vendor, changing the
manifest schema, or changing the WORM policy.

If I name a model in my request, use that one. Do not silently re-route.
```

---

## 5. One-Time Settings Checklist

Do these once, then leave them. They compound the rule's effect.

**Model picker**
- In the chat panel, set your default model to **Composer 2.5 Standard** (not Fast) for Background and Cloud Agents. Cursor picks Fast for interactive chat by default; switch at the start of any long session.
- For Tab completion, no change is needed — Tab is free on all paid plans and does not consume credits.

**Max Mode**
- Leave the Max Mode toggle in the **agent panel off**. Re-enable per-task only when the user explicitly says "Max Mode on".

**Auto mode**
- Keep Auto on. Auto routes routine work to cheap models and is unlimited on Pro/Pro+/Ultra without consuming the $20 credit pool. The rule reinforces Auto's behavior; it doesn't fight it.

**Token-rate / spend alerts**
- Open **Settings → Team / Account → Usage** and confirm the dashboard shows the split between **Cursor Models** (Composer, Grok) and **Other Models** (Claude, GPT, Gemini). This is the surface you audit at the end of each month.
- Set a spend alert at 80% of your included budget so you get a warning before the next bucket starts billing on-demand.

**Rules directory**
- Copy the `.mdc` file above into `.cursor/rules/tape-to-cloud-build.mdc` and commit it. The `Apply Intelligently` type means the rule is included when the agent judges the description matches the chat.
- For global enforcement, paste the User Rule text into Settings → Rules. It is always on.

**Model reveal toggle** (Teams/Enterprise)
- If you are on a plan that has Cursor Router, the routed model is hidden by default. Turn the reveal on for the first 30 days so you can spot-check that the router is matching your expectations. After that, hidden is fine.

---

## 6. The 30-Day Audit Loop

Run this once a month.

1. **Pull the usage dashboard** for the past 30 days. Note the split:
   - **Cursor Models pool** (Composer, Grok, Haiku) — this is your "cheap" spend. Should be ~85–95% of total token volume.
   - **Other Models pool** (Sonnet, Opus, Fable, GPT-5.6 Sol/Terra, Gemini Pro) — this is your "expensive" spend. Should be ~5–15% of total token volume.
2. **Sample 20 chat transcripts** at random. For each, check whether the final response includes the `[model: <name>] [Bucket: …] [module: …]` self-report line the rule requires. If it's missing on most, the rule isn't being followed; tighten the description or move it to `alwaysApply: true`.
3. **For every Bucket C / D call**, check the trigger was actually one of the five listed. If you see expensive calls for docstrings, comments, or the SHA-256 manifest writer, that's a leak. Either update the rule's `never escalate` list or add a per-module example showing the agent what cheap looks like.
4. **Map the 95/5 to the 16 modules.** The cheap 95% should concentrate in `audit`, `disk-ingest`, `tape-vault`, `monetize`, `analytics`, the SHA-256/lifecycle/Postgres scaffolding, and the `ffmpeg`/`tesseract`/`presidio`/tokenization pipeline. The expensive 5% should concentrate in the format-specific readers, the Snowball/Tape Gateway state machine, the WORM-anchor policy, the Temporal workflow design, the Nexus multi-tenant data model, and the chain-of-custody legal posture. If a module is consistently routed to the wrong tier, update the rule's module table.
5. **Compare cost per merged PR** versus the prior month. Cursor's own metric for routing quality is "cost per accepted change" — they reported $4.63 for Auto Balance versus $7.34 for Opus 4.8. If your number is moving the wrong direction, dial up Bucket A and dial down Bucket C.
6. **Check Max Mode usage.** Any time the spend dashboard shows Max Mode billing, ask why. It should be rare, justified, and tied to a >50K token task.

---

## 7. Why This Works for This Specific Project

The blueprint's work splits cleanly into "scaffolding-heavy" (~95%) and "design-heavy" (~5%). Most of the tool is plumbing: an S3-compatible SDK adapter, a SHA-256 manifest writer, a Postgres audit schema, a multipart uploader, a lifecycle policy sweep, a `disk-ingest` reader, a `tape-vault` API integration, an `ffmpeg` proxy pipeline, a `tesseract` OCR call, a `presidio` PII scrubber, a `datatrove` tokenization sharder, a `monetize` license-tag writer, a `restore` orchestrator, a `tape-duplicate` metadata wrapper. None of that needs a frontier model. A cheap model with a clear blueprint reference and `@file` discipline ships it correctly.

The 5% that does need a frontier model is concentrated and recognizable: format-specific readers for proprietary backup-app headers (TSM, NetBackup, Backup Exec, ARCserve, NetWorker, Data Protector, CommVault, Veeam MTF); the AWS Snowball + Tape Gateway OpsHub state machine; the WORM retention-lock policy; the Temporal workflow design with its retry/replay semantics; the Nexus multi-tenant data model; the chain-of-custody legal posture. The rule's escalation list names these explicitly so the agent doesn't have to guess.

The honest ceiling for this project is 90/10 on a disciplined day, 75/25 on a typical week, 50/50 in the first week when the format readers and Temporal design are being worked out. Once those land, the build shifts back to scaffolding and the 95/5 split becomes natural.

---

## 8. One-Sentence Takeaway

Drop the `.mdc` in `.cursor/rules/`, paste the User Rule into Settings, default Composer 2.5 Standard (not Fast) and Grok Code Fast, turn Max Mode off, and audit the Cursor Models vs Other Models split at the end of every month — the cheap 95% scaffolds the 16 modules, the expensive 5% designs the format readers, the Snowball state machine, the WORM policy, the Temporal workflow, the Nexus data model, and the chain-of-custody posture, and the self-report line ties every model call to a specific module so the split is auditable.

---

## References

[1] Cursor Docs — Rules: `.mdc` frontmatter, four rule types (Always / Auto-Attached / Agent Requested / Manual). https://cursor.com/docs/rules

[2] Cursor forum — A Deep Dive into Cursor Rules (>0.45), description-driven inclusion. https://forum.cursor.com/t/a-deep-dive-into-cursor-rules-0-45/60721

[3] Cursor Models & Pricing — full September 2026 lineup, Cursor Models vs Other Models pool split. https://cursor.com/docs/models-and-pricing

[4] Cursor blog — Introducing Cursor Router (Teams/Enterprise), 30–68% cost savings, classifier on 600K+ sessions. https://cursor.com/blog/router

[5] Eigent AI — Cursor Router cost-per-commit data ($4.63 Balance vs $7.34 Opus 4.8). https://www.eigent.ai/blog/cursor-router-model-routing

[6] Verdent — Cursor Pro: $20 included usage, Tab unlimited, Auto unlimited, premium requests draw from pool. https://www.verdent.ai/guides/cursor-usage-limits-explained

[7] Gamsgo — Cursor AI Pricing 2026: Tab and Auto unlimited on paid plans, manual premium model selection burns credits. https://www.gamsgo.com/blog/cursor-pricing

[8] Finout — What Happened to Cursor Pricing: spend alerts rebuilt in June 2026, dashboard splits Cursor Models vs Other Models. https://www.finout.io/blog/what-happened-to-cursor-pricing-2026-guide-5-cost-cutting-tips

[9] Developer Toolkit — Max Mode toggle location, "Off by default, toggle per-task." https://developertoolkit.ai/en/cursor-ide/quick-start/essential-configuration/

[10] Blueprint source — Tape-to-Cloud Migration Tool: Architecture, Use Cases, and Implementation Blueprint (the attached `.md`, originally produced in the prior turn).

<deliver-assets>
<media src="/workspace/mavis-deep-research/20260907_131128_tape_to_cloud_cursor_prompt/final_turn_001.md" caption="Cursor prompt for the tape-to-cloud migration tool: 95/5 model routing + project-specific build instructions" />
</deliver-assets>
