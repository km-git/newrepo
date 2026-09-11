# Expanding the Free-Tool Inventory: A Catalog of GitHub Tools, Python Libraries, and Free-Tier Services for the Tape-to-Cloud Tool

The previous turn shipped a 5-stage improvement loop and a 16-module tool map, but the loop was thin: it named CI/CD plumbing and security scanners, and it left most of the tape-to-cloud tool's *features* without a free library. This turn fills both gaps. The free-tool inventory below adds (a) loop-internal tools that were missing from the prior turn and (b) feature-coverage libraries the tape-to-cloud tool actually needs to deliver the 16 modules. Every entry is free at the 1-person scale unless a gotcha says otherwise, comes with a copy-paste install or curl line, and has a one-line gotcha note. The MinIO call-out at the top is the storage correction: the prior turn's MinIO recommendation is obsolete.

---

## 1. Two Asks

The question "we are missing many other GitHub tools or Python libraries" carries two distinct asks. The first is a loop-internal gap-fill: more tools that *improve* the tool itself (CI, security, code quality, observability, release). The second is a feature-coverage expansion: more libraries that *add* capabilities the 16 modules currently lack (tape control, backup-format parsing, OCR, video transcription, S3-compatible storage, analytics, orchestration, hashing, CLI). The two asks require different categories of free tool, and the answer is organized as such.

| Ask category | What it covers | Where it lives in the tool |
|---|---|---|
| **Loop-internal** | CI runners, security scanners, type checkers, secret scanners, observability SDKs, release tools | The 5-stage loop from the prior turn: discover → evaluate → integrate → verify → release |
| **Feature-coverage** | Tape control, VTL emulation, backup-format parsers, OCR engines, video transcription, S3-compatible storage, analytics engines, workflow orchestrators, hashing libraries, CLI/UX frameworks, schema validation | The 16 modules of the tape-to-cloud blueprint: audit, analytics, vtl-cloud, restore, disk-ingest, email-extract, email-migrate, tape-duplicate, media-ingest, tape-ops, tape-saas, tape-vault, destroy, llm-corpus, ml-enrich, monetize |

The two asks share the 5-stage loop as the chassis, but they pull from different catalogues. The catalogue below is split accordingly.

---

## 2. MinIO Archival and SeaweedFS Replacement

The prior turn's blueprint mentioned MinIO as the self-hosted S3-compatible storage layer. **That recommendation is obsolete.** The public `minio/minio` repository is archived and read-only. GitHub records the archive date as **April 25, 2026** [15]. Secondary write-ups disagree on the exact day: rilavek cites February 14, 2026 [2]; WZ-IT cites April 2026 with a last push on April 24, 2026 [1]. Use the GitHub banner as the canonical date. Pre-built Community Edition binaries and official Docker images were pulled earlier in the retreat; all active development has moved to MinIO AIStor, a commercial product under a proprietary license with capacity-based pricing (~$0.02/GB/month) [1][2]. Any tape-to-cloud deployment that still uses MinIO Community Edition is running on an unmaintained codebase with no security patches.

The 2026 replacement is **SeaweedFS** (Apache 2.0, 34k+ stars, ~512 MB minimum RAM, mature S3 API with IAM, server-side encryption, and tiering) [3]. For setups that want a like-for-like MinIO replacement with a web GUI, **RustFS** (Apache 2.0, Alpha as of early 2026) is the closest successor [2]. For lightweight edge deployments, **Garage** (AGPLv3, 1 GB minimum) is the right pick [2]. The table below covers the live options.

| System | License | Min RAM | S3 API | Web GUI | Status |
|---|---|---|---|---|---|
| **SeaweedFS** | Apache 2.0 | 512 MB | Mature | Included | Active (recommended default) |
| **RustFS** | Apache 2.0 | 2 GB | Good | Included | Alpha (test in dev first) |
| **Garage** | AGPLv3 | 1 GB | Core ops | None (CLI/API) | Active (lightweight) |
| **Ceph RGW** | LGPL 2.1/3 | 16+ GB | Excellent | Dashboard | Active (enterprise) |
| **MinIO CE** | AGPLv3 | 4 GB | Excellent | Browser only | **Archived Apr 25, 2026** [15] |

The deployment question now has a single answer for the tape-to-cloud tool: **SeaweedFS** for the `tape-vault` and `vtl-cloud` modules. The migration path from MinIO is `rclone` (free, MIT) on a cron, copying buckets from the old MinIO endpoint to the new SeaweedFS endpoint; both speak S3, so `rclone sync` works [1].

---

## 3. Loop-Internal Gap Fill

These are the free tools that were missing from the prior turn's 5-stage loop. Each slot is a stage that was under-served; each tool below is a free addition that closes a specific gap.

### 3.1 Code quality: type checkers and docstring coverage

| Tool | Install | Purpose | Gotcha |
|---|---|---|---|
| **mypy** | `uv add --dev mypy` | Static type checker, MIT, the de facto Python standard | Slower than pyright; runs as a separate CI step |
| **pyright** | `uv add --dev pyright` | Microsoft's static type checker, Apache 2.0, faster than mypy on large codebases | Stricter than mypy by default; can produce more warnings on legacy code |
| **interrogate** | `uv add --dev interrogate` | Docstring coverage, MIT, fails CI when public functions lack docstrings | Whitelist noisy modules with `--ignore-magic` and `--ignore-private` |
| **pip-audit** | `uv tool install pip-audit` or `pip-audit` in CI | Python-specific CVE scanner, free, queries OSV.dev under the hood | Needs the resolved dependency tree (`uv pip compile` or `uv.lock`) to give complete results |

The CI step additions to the prior turn's `ci.yml` are minimal: add `mypy .` and `interrogate -vv .` as two more jobs, both with `continue-on-error: false` so they block the PR on a hard type or docstring failure.

### 3.2 Secret and IaC scanning

| Tool | Install | Purpose | Gotcha |
|---|---|---|---|
| **gitleaks** (gitleaks-action) | `gitleaks/gitleaks-action@v2` in CI | Free, GitHub-native, scans every commit + PR for hardcoded secrets [4] | Needs `GITLEAKS_LICENSE` env var for GitHub orgs (not for personal accounts) |
| **TruffleHog** | `trufflesecurity/trufflehog@main` in CI | Free, GitHub-native, verifies secrets are *live* (not just pattern-matched) | Slower than gitleaks; combine both for belt-and-braces |
| **actionlint** | (already in prior turn) | Workflow YAML linter | — |
| **zizmor** | (already in prior turn) | Workflow security scanner | — |

A combined secret-scan + supply-chain CI step uses both gitleaks and TruffleHog in parallel. The git-autoreview benchmark suggests this catches 30-40% more real leaks than gitleaks alone, with the cost of an extra ~30 seconds of CI time per PR [4].

### 3.3 Static analysis at scale: CodeQL

**CodeQL** is GitHub's semantic code analysis engine, free for public repositories. For private repositories, it requires GitHub Code Security at $30 per active committer per month (Secret Protection is a separate $19 per-committer add-on) [5]. For a 1-person shop on a public repository, CodeQL is the highest-value addition to the loop. The integration is one Actions line: `github/codeql-action/analyze@v3` after `github/codeql-action/init@v3` in a `codeql.yml` workflow. CodeQL is the only free static analyzer in this list that understands data flow (e.g., "this user input flows into this SQL query without sanitization"), which Ruff's `S` rules and Semgrep's `p/security-audit` ruleset do not catch.

### 3.4 Release engineering: git-cliff and conventional commits

The prior turn shipped `release-please-action` for changelog generation. The 2026 community default for *richer* changelogs is **git-cliff** (Apache 2.0, Rust binary, Conventional-Commits-based), which supports per-commit grouping, author attribution, and a `cliff.toml` that the operator can check in. The trade-off: `release-please` is GitHub-native and one-file-simple; `git-cliff` produces more polished output but requires a separate binary in CI. For 1-person scale, `release-please` is enough; for a team of 3+ where changelog quality matters, migrate to `git-cliff` via a `git-cliff-action` in the same release workflow.

### 3.5 Observability: OpenTelemetry, GlitchTip, SigNoz

The prior turn listed GlitchTip (BSD, Sentry-SDK-compatible) and SigNoz (Apache 2.0, OTel-native) as Phase-2 add-ons. The missing layer is the **OpenTelemetry Python SDK** (`opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-requests`, `opentelemetry-instrumentation-sqlalchemy`): free, vendor-neutral, and ships traces to any backend. Install:

```bash
uv add opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
uv add opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx
```

The pattern: instrument one module (start with `tape-ops` since it has the most interesting failure modes), export OTLP to SigNoz self-host on a $5/mo VPS, and the loop has full distributed-tracing for free. OneUptime (open source, free self-host) is the alternative if you also want status pages and uptime monitoring bundled in.

### 3.6 Local Actions testing: `act`

**`act`** (`nektos/act`, MIT) runs GitHub Actions locally in Docker. For a 1-person workflow where every commit is a push to `main` with no QA team, `act push` is the closest substitute for a staging branch. Install: `brew install act` or `curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash`. The `act --secret GITHUB_TOKEN=...` flag lets you test Dependabot and release-please locally before pushing.

### 3.7 Actions supply-chain hardening: `step-security/harden-runner`

**`step-security/harden-runner`** (free, MIT) is a drop-in Actions step that runs every job in an egress-firewalled runner. It blocks outbound network calls except to an explicit allowlist (your LLM API, your cloud, your package registries). Add it as the first step in every workflow that touches secrets:

```yaml
- uses: step-security/harden-runner@v2
  with:
    egress-policy: audit
```

`audit` mode logs violations without breaking the build; `block` mode enforces. For the `email-migrate` and `monetize` modules that touch Graph API + Stripe, this is the cheapest defense against a compromised Action exfiltrating customer data.

### 3.8 Paid AI / security / PM / observability SaaS — what we actually use

Those vendors (CodeRabbit, Sourcery, CodeAnt AI, Bito, Greptile, Macroscope, Git AutoReview, Qodo; Mend, Socket, Aikido; Height, Shortcut, Linear; Honeycomb, Sentry) are typically $0 for a tiny team or a 14-day trial, then $12–$60/user/month. This repo stays on the free GitHub-native slot for each:

| Slot | Skip (paid after trial) | Use (free, in-repo or GitHub App) |
|---|---|---|
| AI PR review | Sourcery, CodeAnt, Bito, Greptile, Macroscope, Qodo SaaS | Ruff + CodeQL + Semgrep + reviewdog; PR-Agent when `OPENAI_KEY` is set. CodeRabbit Marketplace is optional (~4 PRs/hr), not required. |
| Supply-chain / SCA | Mend SCA, Socket, Aikido | Dependabot + **Renovate** (`renovate.json`, Mend's free GitHub App) + **dependency-review** Action + pip-audit + OSV |
| Repo posture | Aikido dashboard | **OpenSSF Scorecard** SARIF (`scorecard.yml`) + zizmor + actionlint + gitleaks + TruffleHog |
| PM | Height, Shortcut, Linear | GitHub Issues + existing `dspm-issue-fix` / Dependabot labels |
| Observability | Honeycomb, Sentry cloud | Phase 2: GlitchTip (Sentry-SDK DSN swap) or SigNoz self-host — not a cloud contract |

---

## 4. Feature-Coverage Library Catalog

These are the libraries the tape-to-cloud tool needs to *deliver* the 16 modules' promised features. Each section covers one capability area and ends with the canonical install command.

### 4.1 Tape control and VTL emulation

The blueprint's `audit`, `tape-ops`, `tape-vault`, and `vtl-cloud` modules all need a way to talk to physical or virtual tape hardware. The reference stack is `mt-st` (Linux tape control) + `stenc` (LTO hardware encryption) + `tar` (file-level read/write), and a VTL emulator for dev/CI.

| Tool | License | Install | Purpose | Gotcha |
|---|---|---|---|---|
| **mt-st** | GPL 2 | `apt install mt-st` or build from `github.com/iustin/mt-st` | The reference Linux tape control utility; the prior turn's audit pipeline already wraps this | Needs root to operate physical drives |
| **stenc** | GPL 2 | `apt install stenc` or build from `github.com/scsitape/stenc` | Hardware encryption control for LTO-4+ drives | Drive must support hardware AES-256 |
| **mhvtl** | GPL 2 | `dnf install kmod-mhvtl mhvtl-utils` (ELRepo) or build from `github.com/markh794/mhvtl` | Linux kernel-module-based VTL emulator; the 2010s default | Requires a custom kernel module (`mhvtl.ko`); RHEL-family distros get it pre-built, Debian/Ubuntu need a source build |
| **Holo-VTL** | MIT | `curl -fsSL https://raw.githubusercontent.com/Holo-VTL/Holo/main/scripts/install.sh \| bash` | Rust data plane + Go control plane; uses Linux kernel built-in LIO/TCMU (no custom kernel module); v1.0.4 released June 5, 2026 [6] | Young project (~18 GitHub stars); test in dev before production |
| **LTFS** | Mixed (open format ISO/IEC 20919:2021) | HP or IBM LTFS package per drive vendor | Self-describing tape format; POSIX file APIs after `ltfs mount` | Vendor-specific extensions (HP LTFS vs IBM LTFS vs openLTFS) are not fully compatible |
| **openLTFS** | BSD 3-Clause | Build from `avpres.net/openLTFS` (private beta) | Open-source, vendor-neutral LTFS implementation, ISO/IEC 20919:2021 [6] | Maintenance stopped Spring 2025; private beta only |
| **`tapebackup`** (birdie1) | GPL 2 | Clone `github.com/birdie1/tapebackup` (not on PyPI) | Python tape backup script; pairs with `mt-st` + `stenc` + `tar` | Last updated 2023; small project |

The 1-person default stack is: `mt-st` + `stenc` for the real-drive path; `mhvtl` for the dev/CI VTL; `Holo-VTL` as the 2026 alternative for new deployments on Ubuntu 24.04 LTS.

### 4.2 Backup format parsers

The blueprint's `email-extract`, `disk-ingest`, `media-ingest`, and `audit` modules need to read PST, OST, MSG, MTF, and other backup-app-specific formats. The prior turn had no format parser named; this is the largest single category the prior turn missed.

| Tool | License | Install | Format | Notes |
|---|---|---|---|---|
| **libratom** | MIT | `uv add libratom` | PST, OST, mbox | Entity extraction, .eml export, SQLite output. UNC-Chapel Hill; last PyPI 0.7.1. Compiles libpff during install [7] |
| **libpff-python / pypff** | LGPL | Build from `github.com/libyal/libpff` or use pre-built wheels | PST, OST, PAB | The reference Python binding for the libpff C library; the same parser used by `pst-utils` |
| **pst-utils / libpst** | GPL | `apt install pst-utils` | PST | The C reference implementation; what `readpst` and most PST tools call into |
| **extract-msg** | GPL v3 | `uv add extract-msg` | Outlook .msg | The canonical Python parser for single Outlook message files [17] |
| **PSTmortem** | (see repo) | Clone `github.com/seuffert/pstmortem`; `pip install -r requirements.txt` | PST, OST | Designed for 30+ GB archives with constant memory; resumable Maildir export. **Not on PyPI** — do not `uv add pstmortem` |
| **MailToolbox** | GPL 3.0 | Clone from `github.com/mbucas/MailToolbox` | PST, mbox, Maildir, IMAP, Lotus Notes | Generic source-to-target mail tool; PyQt UI |
| **cvpysdk** | Commvault License | `uv add cvpysdk` | Commvault catalog | Official Commvault Python SDK; reads CommCell metadata over REST. **Not MIT.** Requires a live CommCell with WebConsole (v11 SP7+) |
| **readpst** (libpst) | GPL | `apt install pst-utils` | PST | C reference; the lower layer of `pst_to_mbox.py` and most PST tools |

The reference stack for the `email-extract` module is: `libratom` for the bulk extraction; `extract-msg` for individual messages; `cvpysdk` if the customer is on Commvault *and* you accept the Commvault License plus a live CommCell. The `disk-ingest` module uses `pst-utils` for ad-hoc PSTs found on the disk and `cvpysdk` to walk a Commvault catalog.

### 4.3 Email migration SDKs

The blueprint's `email-migrate` module (GroupWise → M365) needs a real Microsoft Graph SDK. The prior turn mentioned "Graph SDK" abstractly; here is the canonical choice.

| Tool | License | Install | Purpose |
|---|---|---|---|
| **msgraph-sdk** | MIT | `uv add msgraph-sdk azure-identity` | The official Microsoft Graph Python SDK (GA since 2023); fluent API, auto token refresh, built-in retry handler [8] |
| **msgraph-core** | MIT | `uv add msgraph-core` | The lower-level Core library (Kiota-based); use if you want raw HTTP control |
| **imapclient** | New BSD | `uv add imapclient` | IMAP4 client library; covers IMAP-based migrations (e.g., cPanel → M365) |
| **pymap** | MIT | `uv add pymap` | Async IMAP4 client; faster than `imapclient` for high-volume migrations |
| **imap-tools** | Apache 2.0 | `uv add imap-tools` | Higher-level IMAP utilities |

The `email-migrate` module wires `msgraph-sdk` for the M365 destination and `imapclient` for the GroupWise (or any IMAP) source. The `libratom` library handles the PST fallback path. Graph API *calls* are free of SDK cost; an Azure tenant and Graph app registration are still required.

### 4.4 OCR engines

The blueprint's `media-ingest` module digitizes video tapes and documents. OCR turns those images into searchable text. Four free engines cover the spectrum.

| Tool | License | Install | Languages | Speed | Notes |
|---|---|---|---|---|---|
| **Tesseract** (`pytesseract`) | Apache 2.0 | `apt install tesseract-ocr` + `uv add pytesseract` | 100+ | Moderate | The most battle-tested; not the most accurate on complex layouts; backed by Google, 73k+ stars [9] |
| **EasyOCR** | Apache 2.0 | `uv add easyocr` | 80+ | Fast for prototypes | PyTorch-based; the simplest install; ships 80+ language models pre-trained |
| **PaddleOCR** | Apache 2.0 | `uv add paddleocr paddlepaddle` | 100+ | Fast | Layout-aware; the production-grade choice for documents with tables, headers, mixed fonts [9] |
| **Docling** | MIT | `uv add docling` | Depends on backend | Slower but structured | IBM's document parser; turns PDFs into structured Markdown/JSON; uses PaddleOCR or other backends under the hood |
| **Surya** | GPL 3.0 + RAIL | `uv add surya-ocr` | 90+ | Fast | 90+ languages, layout-aware; published by Vik Paruchuri; competitive with PaddleOCR on benchmarks [9] |

The default choice for the `media-ingest` module is **PaddleOCR** for production (layout-aware, 100+ languages) and **EasyOCR** for quick prototypes. Tesseract is the fallback for any environment where PyTorch or PaddlePaddle can't be installed.

### 4.5 Video and audio transcription

The `media-ingest` module also transcribes video tape audio. The 2026 standard is the OpenAI Whisper family, with three free runtime choices depending on hardware.

| Tool | License | Install | Best hardware | Speed | Notes |
|---|---|---|---|---|---|
| **openai/whisper** | MIT | `uv add openai-whisper` | NVIDIA GPU or CPU | Baseline | The reference implementation; simplest path; needs FFmpeg [10] |
| **faster-whisper** | MIT | `uv add faster-whisper` | NVIDIA GPU | 4× faster, 40% less VRAM | CTranslate2 backend; int8 quantization drops VRAM to ~2.5 GB on large-v3 [10][11] |
| **whisper.cpp** | MIT | Build from `github.com/ggerganov/whisper.cpp` | Apple Silicon, CPU, edge | Fast via Metal/Core ML | C/C++ port; zero Python dependency; runs on Raspberry Pi [10] |
| **Distil-Whisper** | MIT | `uv add transformers` + Hugging Face checkpoint | NVIDIA GPU or CPU | 6× faster | Hugging Face distilled; ~50% smaller; within 1% WER of large-v3 [10] |
| **yt-dlp** | Unlicense | `uv add yt-dlp` | n/a | n/a | Video extraction; pairs with Whisper for YouTube-to-transcript pipelines |

The pick-by-hardware rule, verified by 2026 benchmarks: **faster-whisper on NVIDIA GPUs (Linux/Windows)**, **whisper.cpp on Apple Silicon (Mac)**, **Distil-Whisper when speed matters more than the last 1% of WER**. All three accept the same Whisper checkpoints (tiny, base, small, medium, large-v3), so the model choice is independent of the runtime choice.

### 4.6 S3-compatible storage: post-MinIO

Section 2 covered the MinIO replacement. The install lines for the 2026 default are:

```bash
# SeaweedFS — the recommended default [3]
curl -fsSL https://raw.githubusercontent.com/seaweedfs/seaweedfs/master/install.sh | bash
AWS_ACCESS_KEY_ID=admin AWS_SECRET_ACCESS_KEY=secret S3_BUCKET=tape-vault \
  weed mini -dir=./data
# S3 endpoint: http://localhost:8333
```

```bash
# RustFS — MinIO-style with web GUI (Alpha) [16]
curl -O https://rustfs.com/install_rustfs.sh && bash install_rustfs.sh
```

```bash
# Python S3 client (talks to any of the above)
uv add boto3 aioboto3 obstore
```

The Python layer uses `boto3` (AWS, Apache 2.0) for the standard path, `aioboto3` (Apache 2.0) for async high-throughput, and `obstore` (Apache 2.0, Rust-based) for the performance-critical paths in `tape-vault` and `vtl-cloud`. For S3-on-S3 metadata operations (versioning, lifecycle), use `boto3` directly.

### 4.7 Analytics: DuckDB, Polars, and PyArrow

The blueprint's `analytics` module queries 1M+ rows of post-migration reports. Pandas breaks on this size. The 2026 standard is a three-tool hybrid: DuckDB for SQL, Polars for DataFrame transformations, PyArrow as the columnar-memory glue.

| Tool | License | Install | Use when | Performance vs Pandas |
|---|---|---|---|---|
| **DuckDB** | MIT | `uv add duckdb` | SQL on files (Parquet, CSV, JSON) directly; no loading step; spills to disk automatically | 9.4× faster on aggregations [12] |
| **Polars** | MIT | `uv add polars` | DataFrame transformations on in-memory data; lazy evaluation; Apache Arrow native | 8.7× faster on groupby; 30-60% less peak memory [12] |
| **PyArrow** | Apache 2.0 | `uv add pyarrow` | Columnar memory format; zero-copy handoffs between DuckDB, Polars, and Pandas | The transport layer; not a DataFrame library itself |

The pattern: DuckDB does the SQL aggregation on Parquet files in the `tape-vault`, hands the result to Polars as a zero-copy Arrow table, Polars does the column transformations, PyArrow serializes the result back to Parquet. Pandas is reserved for the final mile (sklearn, matplotlib). The hybrid can be introduced one module at a time, with DuckDB as the first addition (a single SQL query can replace a 50-line Pandas groupby).

### 4.8 Workflow orchestration

The blueprint's `restore` module needs a workflow orchestrator that survives multi-day restore jobs. Four free options cover different needs.

| Tool | License | Self-host | Best for | Operational weight |
|---|---|---|---|---|
| **Apache Airflow** | Apache 2.0 | Free | Scheduled tasks; the biggest ecosystem | Heavy (scheduler + executor + metadata DB + webserver) |
| **Prefect** | Apache 2.0 | Free (Hobby plan on Prefect Cloud) | Python-first; dynamic workflows; light ops | Medium |
| **Dagster** | Apache 2.0 | Free | Asset-centric; lineage-critical pipelines | Medium |
| **Temporal** | MIT | Free self-host | Durable execution; multi-day jobs that survive crashes | Heavy (Cassandra or Postgres + Elasticsearch for self-host) [13] |

**Temporal Cloud is not a free production tier.** New accounts get $1,000 in credits that expire after 90 days. After that, Essentials starts at $100/month and includes 1M actions [18]. The $0 path is self-hosting the MIT server.

The decision rule: **Airflow, Prefect, or Dagster** for *scheduled* workflows (nightly audit, weekly report generation). **Temporal** for *durable* workflows (a multi-day restore job where a worker crash must not lose progress; the job restarts from where it left off). For the tape-to-cloud tool, the right answer is **self-hosted Temporal for `restore` + `email-migrate`** (these are the long-running, crash-recoverable workflows) and **Prefect or Dagster for `audit` + `analytics`** (these are the scheduled, ETL-shape workflows). Fall back to Temporal Cloud only if self-host ops cost more than $100/month.

### 4.9 Hashing and signing

The blueprint's `audit` and `destroy` modules need cryptographic hashing for chain-of-custody. Two tools cover the spectrum.

| Tool | License | Install | FIPS-approved | Speed | Use when |
|---|---|---|---|---|---|
| **hashlib.sha256** (stdlib) | Public domain | (built in) | Yes (FIPS 180-4) | Baseline | Chain-of-custody for regulated data; the default for `audit` and `destroy` |
| **blake3** (Python binding) | CC0 / Apache 2.0 | `uv add blake3` | No (no NIST/FIPS status) | Up to 27× faster than SHA-256 on large files; multi-threaded | Non-compliance throughput work; dedup; content-addressed storage [14] |

The decision rule: **SHA-256 for anything that touches a customer chain-of-custody record.** **BLAKE3 for non-compliance hashing** (dedup of millions of small files, content-addressed keys in the LLM-corpus module). Mixing the two is fine; just label which hash is which in the metadata.

### 4.10 CLI and UX

The blueprint's modules need a real CLI. The 2026 standard is `typer` (MIT, Click successor by the FastAPI author) + `rich` (MIT, beautiful terminal output) + `textual` (MIT, full TUI).

```bash
uv add typer rich textual httpx pydantic pydantic-settings
```

`typer` is the entry-point library (replaces Click; less boilerplate; type-hint-driven). `rich` adds progress bars, tables, syntax highlighting, and tracebacks. `textual` is for a full TUI dashboard if the operator wants one. `httpx` is the modern `requests` successor with HTTP/2 and async support. `pydantic` v2 is the schema-validation standard (5-50× faster than v1; Rust core).

### 4.11 Schema and data validation

`pydantic` v2 (MIT) is the canonical choice for every module that produces or consumes structured data. The `audit` module produces a JSON manifest; `restore` accepts a typed config; `monetize` processes billing events. The install line above covers it.

For more aggressive validation, **`attrs` + `cattrs`** (both MIT) is a lighter-weight alternative to pydantic for hot-path code. The 2026 default is still pydantic v2; reach for `attrs` only when pydantic's overhead is profiled to be the bottleneck.

### 4.12 AI/LLM cost and eval

The blueprint's `llm-corpus` and `ml-enrich` modules make many LLM API calls. Free tooling exists to gate the cost and quality of those calls.

| Tool | License | Install | Purpose |
|---|---|---|---|
| **litellm** | MIT | `uv add litellm` | Unified interface to 100+ LLM providers; built-in cost tracking; free proxy mode |
| **instructor** | MIT | `uv add instructor` | Structured-output (Pydantic-validated) extraction from LLM responses; free |
| **pydantic-evals** | MIT | `uv add pydantic-evals` | Evaluation framework for LLM outputs; integrates with `instructor` |
| **OpenLLMetry** | Apache 2.0 | `uv add opentelemetry-instrumentation-openai` | OTel-native LLM call tracing; ships spans to SigNoz/Honeycomb/etc. |

The `llm-corpus` module wires `litellm` as the unified LLM client, `instructor` to enforce the response schema, and `pydantic-evals` to run regression checks on a golden dataset. OpenLLMetry is the observability layer for the LLM calls; it exports OTLP to the SigNoz self-host from section 3.5. LLM *API* tokens remain a separate budget; these libraries do not make the model calls free.

---

## 5. Comparison Tables for Multi-Option Choices

Three choices in the catalogue are too close to call without side-by-side data. The tables below capture the trade-offs that matter for the tape-to-cloud tool.

### 5.1 OCR engines for the `media-ingest` module

| Engine | Languages | Layout-aware | Best for | Install effort |
|---|---|---|---|---|
| **Tesseract** | 100+ | No | The most battle-tested, lowest install overhead, when layout is simple | `apt install` + `uv add pytesseract` |
| **EasyOCR** | 80+ | No | Quick prototypes, when accuracy is "good enough" | `uv add easyocr` (PyTorch wheels) |
| **PaddleOCR** | 100+ | Yes | Production: tables, mixed fonts, complex layouts | `uv add paddleocr paddlepaddle` (larger install) |
| **Surya** | 90+ | Yes | Multilingual, layout-aware, modern ML alternative to PaddleOCR | `uv add surya-ocr` |
| **Docling** | Depends on backend | Yes (outputs structured JSON/Markdown) | PDFs that need to be parsed into structured records, not just OCR'd | `uv add docling` |

The default for `media-ingest`: **PaddleOCR for production, EasyOCR for prototypes, Tesseract as the always-works fallback.**

### 5.2 Analytics engines for the `analytics` module

| Engine | Style | Best for | Memory ceiling |
|---|---|---|---|
| **DuckDB** | SQL-first; queries files directly | "SQLite for analytics"; large aggregation queries on Parquet files in the `tape-vault` | Spills to disk; no OOM |
| **Polars** | DataFrame API; lazy evaluation | Pipeline transformations; in-process analytics; ML feature engineering | In-memory; 30-60% less peak than Pandas |
| **PyArrow** | Columnar memory format | The transport layer between DuckDB and Polars; not a DataFrame library | n/a |

The default for `analytics`: **DuckDB + Polars + PyArrow as a three-tool stack.** DuckDB does the SQL on files; Polars does the DataFrame work; PyArrow is the zero-copy glue. Pandas is for the final-mile integration with sklearn or matplotlib.

### 5.3 Workflow orchestrators

| Orchestrator | Model | Best for | Operational cost |
|---|---|---|---|
| **Apache Airflow** | Task-centric DAGs | Scheduled ETL; the biggest community | Heavy (PostgreSQL + scheduler + executor + webserver) |
| **Prefect** | Python-first flows | Lighter ops; dynamic workflows; free Hobby tier on Prefect Cloud | Medium |
| **Dagster** | Asset-centric | Pipelines built around data assets (tables, partitions, lineage) | Medium |
| **Temporal** | Durable execution | Multi-day workflows that survive worker crashes (the `restore` and `email-migrate` use cases) | Heavy self-host; Cloud Essentials from $100/mo [18] |

The default for the tape-to-cloud tool: **self-hosted Temporal for `restore` and `email-migrate`** (the long-running, crash-recoverable workflows). **Prefect or Dagster for `audit` and `analytics`** (the scheduled, ETL-shape workflows).

---

## 6. Per-Module Expansion Map

The 16 modules from the blueprint each now have 3-7 free tools, not 1-2. The map below is the consumption view of the catalogue. Every tool listed is free at the 1-person scale unless a gotcha in sections 4.2 or 4.8 applies; the install line is shown where it differs from a `uv add` already covered above.

| # | Module | Free tools (in addition to prior turn) | Install |
|---|---|---|---|
| 1 | **audit** | `mt-st` + `stenc` for real drives; `mhvtl` for VTL emulator; `libratom` for catalog reading; `blake3` for non-compliance dedup; `pydantic` for manifest schema | `apt install mt-st stenc`; `uv add libratom pydantic blake3` |
| 2 | **analytics** | DuckDB + Polars + PyArrow (the three-tool hybrid); `litellm` for LLM-backed query expansion | `uv add duckdb polars pyarrow`; `uv add litellm` |
| 3 | **vtl-cloud** | `mhvtl` (or `Holo-VTL` for 2026 deployments); SeaweedFS as the S3 backend; `ltfs` for self-describing tape I/O | `dnf install kmod-mhvtl mhvtl-utils`; SeaweedFS install from section 4.6 |
| 4 | **restore** | Self-hosted Temporal for durable multi-day restore jobs; `libratom` for catalog recovery; `blake3` for verification hashing | `uv add temporalio`; `uv add libratom blake3` |
| 5 | **disk-ingest** | `libratom` for PST/OST found on disk; `pst-utils` for the C reference; `cvpysdk` for Commvault catalog walking | `apt install pst-utils`; `uv add libratom cvpysdk` |
| 6 | **email-extract** | `libratom` for PST/OST/mbox; `extract-msg` for .msg; PSTmortem (clone) for 30+ GB archives | `uv add libratom extract-msg`; clone `seuffert/pstmortem` |
| 7 | **email-migrate** | `msgraph-sdk` + `azure-identity` for M365 destination; `imapclient` for IMAP source; Temporal for durable multi-day migrations | `uv add msgraph-sdk azure-identity imapclient temporalio` |
| 8 | **tape-duplicate** | `mt-st` + `stenc` for real drives; `mhvtl` for dev/CI; `blake3` for verification | `apt install mt-st stenc`; `uv add blake3` |
| 9 | **media-ingest** | PaddleOCR for production OCR; EasyOCR for prototypes; Tesseract as fallback; Whisper (faster-whisper on NVIDIA, whisper.cpp on Mac, Distil-Whisper for speed); `ffmpeg` for video decode | `uv add paddleocr easyocr pytesseract faster-whisper`; `apt install ffmpeg` |
| 10 | **tape-ops** | `mt-st` + `stenc`; `mhvtl` for VTL; `typer` + `rich` for the CLI surface; OTel SDK for traces | `apt install mt-st stenc`; `uv add typer rich opentelemetry-instrumentation-httpx` |
| 11 | **tape-saas** | SeaweedFS (or Garage for edge); GlitchTip or SigNoz for the SaaS observability layer; `litellm` if the SaaS has an LLM feature | SeaweedFS install; `uv add sentry-sdk` (GlitchTip is Sentry-SDK-compatible) |
| 12 | **tape-vault** | SeaweedFS as the S3 backend; DuckDB for the catalog query layer; `lakefs` if git-like versioning of the vault is needed; `blake3` for content addressing | SeaweedFS install; `uv add duckdb blake3` |
| 13 | **destroy** | `cosign` (already in prior turn) for signed destruction certificates; `blake3` for fast purge verification; `pyca/cryptography` for any custom crypto | `uv add blake3 cryptography` |
| 14 | **llm-corpus** | `litellm` (unified LLM client); `instructor` (structured output); `pydantic-evals` (regression checks); `blake3` for content addressing; `duckdb` for the corpus catalog; `polars` for preprocessing | `uv add litellm instructor pydantic-evals blake3 duckdb polars` |
| 15 | **ml-enrich** | `polars` + `pyarrow` for feature engineering; DuckDB for offline eval; `litellm` if the enricher calls an LLM; OTel SDK for tracing | `uv add polars pyarrow duckdb litellm` |
| 16 | **monetize** | `msgraph-sdk` if billing exports to M365; GlitchTip for usage-event tracking; SeaweedFS for the billing-event archive; `pydantic` for the invoice schema | `uv add pydantic sentry-sdk` |

The map shows the 16 modules' true surface area. Each row is 3-7 free tools, not 1-2. The total dependency count is bounded: roughly 20 `uv add` lines cover the whole tool, and 6 system-level packages (`mt-st`, `stenc`, `mhvtl`, `tesseract`, `ffmpeg`, `pst-utils`) cover the rest. PSTmortem stays a git clone, not a PyPI pin.

---

## 7. Single `pyproject.toml` Install Matrix

The full set of new dependencies, organized by purpose, fits in one `pyproject.toml` block. Combine with the prior turn's `pyproject.toml` (Ruff config) to get the complete dependency surface.

```toml
[project]
requires-python = ">=3.12"
dependencies = [
    # HTTP / schema
    "httpx>=0.27",
    "pydantic>=2.8",
    "pydantic-settings>=2.4",
    # LLM
    "litellm>=1.50",
    "instructor>=1.3",
    "pydantic-evals>=0.1",
    # AWS / S3
    "boto3>=1.35",
    "aioboto3>=13.0",
    "obstore>=0.5",
    # Analytics
    "duckdb>=1.0",
    "polars>=1.0",
    "pyarrow>=17.0",
    # Tape / VTL parsers
    "libratom>=0.7",
    "extract-msg>=0.48",
    "cvpysdk>=11.0",
    # Email migration
    "msgraph-sdk>=1.0",
    "azure-identity>=1.16",
    "imapclient>=3.0",
    # OCR
    "pytesseract>=0.3",
    "easyocr>=1.7",
    "paddleocr>=2.7",
    # Transcription
    "faster-whisper>=1.0",
    "yt-dlp>=2024.5",
    # Hashing
    "blake3>=1.0",
    "cryptography>=43.0",
    # Orchestration
    "temporalio>=1.9",
    # Observability
    "opentelemetry-api>=1.27",
    "opentelemetry-sdk>=1.27",
    "opentelemetry-exporter-otlp>=1.27",
    "opentelemetry-instrumentation-fastapi>=0.48b0",
    "opentelemetry-instrumentation-httpx>=0.48b0",
    "sentry-sdk>=2.0",  # also works with GlitchTip
]

[dependency-groups]
dev = [
    # Quality
    "ruff>=0.16",
    "mypy>=1.11",
    "pyright>=1.1",
    "interrogate>=1.7",
    # Security
    "pip-audit>=2.7",
    # Pre-commit
    "prek>=0.5",
]
```

`pstmortem` is omitted on purpose: it is not published on PyPI. Vendoring it as a git submodule or `tool.uv.sources` git URL is the honest pin. `cvpysdk` is included because it is on PyPI, but it is Commvault-licensed and needs a live CommCell; drop it until a Commvault customer exists.

The block is heavy (~30 production deps) but every entry is a single-purpose tool with no per-call cost except LLM API tokens and optional Temporal Cloud. The 1-person scale can use all of them; the operator can remove a group if the corresponding module isn't built yet.

---

## 8. Discovery Sources

The "Discover" slot of the 5-stage loop needs more than Track Awesome List. The sources below are free RSS feeds or browseable indexes that the operator can read on the Monday review.

| Source | What it tracks | How to subscribe |
|---|---|---|
| **Track Awesome List** (prior turn) | 500+ awesome-* list diffs | RSS at `trackawesomelist.com` |
| **awesome-selfhosted** (GitHub) | Self-hosted software alternatives; updated weekly | `github.com/awesome-selfhosted/awesome-selfhosted` releases.atom |
| **GitHub Topics** | Topic-tagged repos (e.g., `tape`, `ltfs`, `pst`, `ocr`, `lto`) | `github.com/topics/<topic>` RSS |
| **libraries.io** | PyPI, npm, Maven, etc. package tracking | Email digest or API |
| **oss.fund** | Open-source sustainability and project health | Web browse; weekly |
| **changelog.com podcast** | Open-source project news | RSS |
| **GitHub releases.atom** (per repo) | Every release of a tracked repo | `github.com/<owner>/<repo>/releases.atom` |
| **AI Web Feeds** (aiwebfeeds.vercel.app) | LLM SDK and model release feeds (prior turn) | RSS |
| **GitHub Marketplace /actions** | New GitHub Actions | `github.com/marketplace?type=actions` weekly browse |

The Monday review expands: open the Dependabot dashboard, open the Renovate dashboard, open the Security tab, read the model feed, then browse `awesome-selfhosted` for the 3 sections that match the 16 modules. Anything new goes into the candidate list for the next `Evaluate` step.

---

## 9. Failure Modes and Expansions

A richer tool inventory means more failure modes. The table below covers the 5 most likely new failure modes, with recovery.

| Failure mode | What happens | Recovery |
|---|---|---|
| **mhvtl kernel module breaks on a kernel upgrade** | The VTL emulator stops working; CI fails to spin up tape tests | Pin the dev/CI runners to a known-good kernel; or migrate to `Holo-VTL` which uses the kernel's built-in LIO/TCMU and has no custom module [6] |
| **A new BLAKE3 CVE drops** | The hash function is now on a watch list | Switch to `hashlib.sha256` for new chain-of-custody records; keep BLAKE3 for internal dedup only [14] |
| **Tesseract OCR accuracy is too low for a customer** | The `media-ingest` module produces unusable text | Add PaddleOCR as a fallback; route the same image through both engines, diff the output, flag conflicts for human review |
| **Temporal self-host is too operationally heavy** | The `restore` jobs fail to start because the Cassandra/Postgres/Elasticsearch stack is down | Use Temporal Cloud ($1,000 / 90-day credits, then $100/mo Essentials) [18], or fall back to Prefect for the long-running workflows |
| **A new OCR model ships (e.g., a major PaddleOCR release)** | The `media-ingest` module runs the old model with the same prompts | The model feed watcher (prior turn) catches the SDK release; bump the PaddleOCR pin in `pyproject.toml`, re-run the golden dataset through `pydantic-evals` to confirm no regression, deploy |

The most important expansion-time rule: **every new tool has a named fallback.** OCR falls back from PaddleOCR to EasyOCR to Tesseract. Storage falls back from SeaweedFS to Garage to Ceph. Orchestration falls back from Temporal to Prefect. The pattern is the same as the prior turn's loop-internal resilience.

---

## 10. Cost Ceiling

The 1-person-scale software cost ceiling stays $0 for the libraries themselves. Two items are *not* $0 if you choose the hosted path: Temporal Cloud after the 90-day credit window, and any LLM API tokens. The breakdown:

| Category | New free tools | Cost |
|---|---|---|
| **Tape control + VTL** | mt-st, stenc, mhvtl, Holo-VTL, openLTFS, tapebackup | $0 (system packages + GitHub-hosted runners) |
| **Backup format parsers** | libratom, extract-msg, PSTmortem, cvpysdk, pst-utils | $0 (PyPI + system packages); cvpysdk needs a customer CommCell |
| **Email migration** | msgraph-sdk, imapclient, pymap | $0 (PyPI; Azure tenant is free for the SDK itself) |
| **OCR** | Tesseract, EasyOCR, PaddleOCR, Surya, Docling | $0 (PyPI + system packages) |
| **Transcription** | openai-whisper, faster-whisper, whisper.cpp, Distil-Whisper, yt-dlp | $0 (PyPI + system packages) |
| **S3-compatible storage** | SeaweedFS, RustFS, Garage | $0 (self-host on existing $5/mo VPS) |
| **Analytics** | DuckDB, Polars, PyArrow | $0 (PyPI; runs on the same VPS) |
| **Orchestration** | Airflow, Prefect, Dagster, Temporal (self-host) | $0 self-host OSS; Temporal Cloud Essentials from $100/mo after $1,000 / 90-day credits [18] |
| **Hashing** | blake3, hashlib.sha256, cryptography | $0 (PyPI) |
| **CLI/UX** | typer, rich, textual, httpx, pydantic | $0 (PyPI) |
| **LLM tooling** | litellm, instructor, pydantic-evals, OpenLLMetry | $0 (PyPI; LLM API calls themselves are a separate budget) |
| **Discovery** | awesome-selfhosted, libraries.io, GitHub Topics, AI Web Feeds | $0 (RSS + browse) |
| **Code quality (prior turn + this turn)** | Ruff, mypy, pyright, interrogate, pip-audit | $0 (PyPI) |
| **Security (prior turn + this turn)** | Gitleaks, TruffleHog, OSV-Scanner, CodeQL | $0 (free for public repos; CodeQL is paid on private repos [5]) |

The only new spend beyond the prior turn is the optional $5-10/mo VPS for SeaweedFS + GlitchTip + SigNoz self-host, plus Temporal Cloud *if* you decline to self-host. Everything else is $0 at 1-person scale on public repositories.

---

## 11. Inventory Summary

The prior turn's 5-stage loop is the chassis. This turn fills the chassis with the *specific* free Python libraries the tape-to-cloud tool needs to (a) keep itself current and (b) actually *deliver* the 16 modules' promised features. The biggest corrections to the prior turn: **MinIO Community Edition is archived (GitHub: April 25, 2026); use SeaweedFS**; **gitleaks + TruffleHog + CodeQL are the missing security layers**; **mhvtl + Holo-VTL are the missing VTL emulators for dev/CI**; **libratom + msgraph-sdk + cvpysdk are the missing backup-format and email-migration libraries**; **PaddleOCR + faster-whisper are the missing media-ingest engines**; **DuckDB + Polars + PyArrow is the missing analytics stack**; **self-hosted Temporal is the right orchestrator for the long-running restore/email-migrate workflows**; **BLAKE3 is the missing throughput hash, but SHA-256 stays the default for chain-of-custody**.

Fact-check notes against the draft that started this turn:

- MinIO archive date is **April 25, 2026** on GitHub [15], not February 14.
- `libratom` is **MIT**, not Apache 2.0 [7].
- `extract-msg` is **GPL v3**, not MIT [17].
- `cvpysdk` is **Commvault License**, not MIT; it needs a live CommCell.
- `pstmortem` is **not on PyPI**; clone `seuffert/pstmortem`.
- RustFS install is `https://rustfs.com/install_rustfs.sh`, not a GitHub `raw/.../install.sh` path [16].
- Temporal Cloud is **not** a free 1M-actions/month plan; that allocation sits on paid Essentials ($100/mo) [18].

The expanded inventory is the consumable form of the loop: every Discover finding, every Evaluate decision, every Integrate PR, and every Verify check now has a named, free, copy-paste-installable tool. The 5-stage loop + the 16-module map + the install matrix + the failure modes + the cost ceiling = the complete self-sustaining improvement system.

---

## 12. References

[1] wz-it, "MinIO is archived: self-hosted S3-compatible storage compared," August 2026. https://wz-it.com/en/blog/minio-successor-s3-storage-comparison/

[2] rilavek, "Self-Hosted S3 Storage in 2026: RustFS, SeaweedFS, Garage, or MinIO?" 2026. https://rilavek.com/resources/self-hosted-s3-compatible-object-storage-2026

[3] SeaweedFS GitHub repository, "SeaweedFS is a distributed storage system for object storage, files, and Iceberg tables," 2026. https://github.com/seaweedfs/seaweedfs

[4] oneuptime, "How to Run Security Scanning with GitHub Actions," January 2026. https://oneuptime.com/blog/post/2026-01-25-security-scanning-github-actions/view

[5] GitHub Docs, "GitHub Advanced Security license billing," 2026. https://docs.github.com/en/billing/concepts/product-billing/github-advanced-security

[6] Holo-VTL/Holo, v1.0.4 release, June 5, 2026. https://github.com/Holo-VTL/Holo/releases/tag/v1.0.4

[7] libratom GitHub repository, MIT License, "Python library and supporting utilities to parse and process PST and mbox email sources." https://github.com/libratom/libratom

[8] Microsoft, "Introducing the Microsoft Graph Python SDK," 2023 (GA). https://devblogs.microsoft.com/microsoft365dev/introducing-the-microsoft-graph-python-sdk/

[9] Unstract, "Best Open Source OCR Tools & Models in 2026," 2026. https://unstract.com/blog/best-opensource-ocr-tools/

[10] SYSTRAN, "Faster Whisper transcription with CTranslate2," 2026. https://github.com/SYSTRAN/faster-whisper

[11] promptquorum, "Whisper.cpp vs faster-whisper 2026: STT Speed Test," 2026. https://www.promptquorum.com/power-local-llm/local-whisper-stt-comparison-2026

[12] birjob, "Polars vs DuckDB vs Pandas: The 2026 Decision Guide," 2026. https://www.birjob.com/blog/polars-duckdb-pandas-2026-decision-guide

[13] futurepicker, "Temporal vs Airflow vs Prefect vs Dagster 2026," 2026. https://futurepicker.com/en/workflow-orchestration-temporal-airflow-prefect-dagster-2026/

[14] shattered.io, "BLAKE3 vs SHA-256: Up to 27x Faster, No FIPS," 2026. https://shattered.io/blake3-vs-sha256-2026/

[15] GitHub, minio/minio repository archive notice, April 25, 2026. https://github.com/minio/minio

[16] rustfs/rustfs, Apache 2.0, one-click install. https://github.com/rustfs/rustfs

[17] extract-msg, PyPI, GPL v3. https://pypi.org/project/extract-msg/

[18] Temporal Cloud pricing, Essentials from $100/month including 1M Actions; $1,000 credits expire after 90 days. https://docs.temporal.io/cloud/pricing
