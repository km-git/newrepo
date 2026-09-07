# Forum-Monitoring Subsystem for the Tape-to-Cloud Tool

A weekly GitHub-Actions-cron pipeline that turns Reddit, Hacker News, Stack Overflow, Lobsters, GitHub Discussions, vendor blogs, and OSS mailing lists into Discover-slot candidates for the 5-stage improvement loop, hands them to the operator as a single Monday-9 AM Australia/Sydney pull request, and stays on the free tier.

Copy-paste kit: `forum-watcher/` in this repo (flatten into a dedicated `t2c-forum-watcher` repo, or keep the nested layout and use `.github/workflows/forum-watcher.yml` here).

---

## 1. Subsystem Overview

The watcher is a four-stage pipeline — **fetch → dedupe → classify → deliver** — wired to a four-axis triage rubric and a Dependabot-style weekly pull request. It runs once a week inside GitHub Actions (Monday 09:00 `Australia/Sydney`), fans out 15-20 HTTP requests in parallel against free community endpoints, dedupes every new item by SHA-256 of the URL, runs each new item through a free-LLM classifier that assigns a 16-module tag plus a 0-12 score, writes a single `discoveries/YYYY-MM-DD.md` file, and opens a pull request via `peter-evans/create-pull-request@v8`. The operator opens the PR Monday morning, checks the boxes for items worth promoting to Evaluate, merges, and the auto-trigger opens Evaluate-slot issues. Total weekly time: about five minutes. Total monthly software cost: zero. Total annual coverage: roughly 20 sources × 16 modules.

---

## 2. 2026 Platform Changes

Three platform facts make a free, copy-paste-ready forum watcher viable in 2026.

**GitHub Actions cron now has IANA timezones.** As of 19 March 2026, the `on.schedule` block accepts a sibling `timezone:` field with an IANA name and handles DST automatically [1]. Before that, workflows were UTC-only and the workaround for "9 AM Sydney" was two cron entries gated by date checks. The watcher uses one entry: `cron: '0 9 * * 1'` with `timezone: 'Australia/Sydney'`, which fires Monday 09:00 *wall clock* in Sydney (AEST in winter, AEDT in summer). Older guides that say "UTC-only, offset manually" are obsolete.

**The Reddit `.rss` suffix still serves an Atom feed without auth.** Appending `.rss` to almost any subreddit URL returns recent items with no OAuth, no API key, no account [2]. Datacenter IPs do get 403 in some configurations, but a weekly cron is usually fine. Verified 2026-09-07 from this environment: `https://www.reddit.com/r/sysadmin/.rss` returned HTTP 200 Atom (`<feed xmlns="http://www.w3.org/2005/Atom">`) with `<updated>2026-09-07T06:37:09+00:00</updated>`.

**Hacker News ships two free, unauthenticated APIs.** The official Firebase API at `hacker-news.firebaseio.com/v0/` is the canonical source for one item by ID or a top-500 list [3]. The Algolia API at `hn.algolia.com/api/v1/` adds full-text search, date filters, tag filters, and pagination, and has a 10,000-requests-per-hour-per-IP rate limit [4]. The watcher uses Algolia **JSON** (`kind: algolia`) for "watch this topic" queries and never mixes the two. Use `https://`, not `http://`. Verified 2026-09-07: `search_by_date?query=tape OR ltfs OR lto` returned HTTP 200 with hits.

One constant that did not change: getting a Reddit API key in 2026 is still hard for personal projects, and the workaround everyone reaches for is the same `.rss` suffix [5]. The watcher treats Reddit as RSS-only.

---

## 3. Free Sources Mapped to the 16 Modules

The 16 modules of the tape-to-cloud tool are: `audit`, `analytics`, `vtl-cloud`, `restore`, `disk-ingest`, `email-extract`, `email-migrate`, `tape-duplicate`, `media-ingest`, `tape-ops`, `tape-saas`, `tape-vault`, `destroy`, `llm-corpus`, `ml-enrich`, `monetize`. A forum post is in scope if it touches any of these.

Live checks on 2026-09-07 changed three rows versus a naive copy of common URLs:

- Stack Overflow `/feeds/tag/tape` and `/feeds/tag/ltfs` return **HTTP 404**. `/feeds/tag/backup` and `/feeds/tag/lto` return Atom 200. The Stack Exchange API `tagged=tape;lto` returned **zero items** (semicolon is AND, and `tape` is empty); `tagged=backup` returned items. Use the API for JSON, not Cloudflare-fragile HTML, and do not poll empty tags.
- Lobsters `/t/storage.rss` returns **HTTP 404** (no such tag). `/t/hardware.rss`, `/t/linux.rss`, `/t/devops.rss` return RSS 2.0 200.
- Borg `releases.atom` returned Release 2.0.0b24, 2.0.0b23, 1.4.5 as claimed [7].

| # | Source | Endpoint | Free tier | Primary modules |
|---|--------|----------|-----------|-----------------|
| 1 | Reddit `r/sysadmin` | `https://www.reddit.com/r/sysadmin/.rss` | Atom, weekly cron safe [2] | `tape-ops`, `disk-ingest`, `restore`, `vtl-cloud` |
| 2 | Reddit `r/DataHoarder` | `https://www.reddit.com/r/DataHoarder/.rss` | same | `media-ingest`, `tape-vault`, `monetize` |
| 3 | Reddit `r/homelab` | `https://www.reddit.com/r/homelab/.rss` | same | `disk-ingest`, `media-ingest` |
| 4 | Reddit `r/selfhosted` | `https://www.reddit.com/r/selfhosted/.rss` | same | `disk-ingest`, `tape-vault` |
| 5 | Reddit `r/BorgBackup` | `https://www.reddit.com/r/BorgBackup/.rss` | same | `disk-ingest`, `media-ingest` |
| 6 | Reddit `r/Veeam` | `https://www.reddit.com/r/Veeam/.rss` | same | `vtl-cloud`, `restore` |
| 7 | Hacker News Algolia | `https://hn.algolia.com/api/v1/search_by_date?query=...&tags=story&hitsPerPage=25` | 10K req/hr/IP, no auth [4] | `tape-ops`, `monetize`, `llm-corpus` |
| 8 | Hacker News Firebase top | `https://hacker-news.firebaseio.com/v0/topstories.json` | unauth [3]; skip on day one (N+1 ID fetches) | cross-module signal |
| 9 | Stack Overflow tag `backup` | `https://stackoverflow.com/feeds/tag/backup` | Atom, dense. Do **not** use tag `lto` — on SO that is compiler link-time optimization, not Linear Tape-Open | `disk-ingest`, `restore`, `vtl-cloud` |
| 10 | Stack Exchange API `backup` | `https://api.stackexchange.com/2.3/questions?...&tagged=backup&site=stackoverflow` | 10K req/day with key, 300 without [6] | `disk-ingest`, `restore` |
| 11 | Lobsters tag `hardware` | `https://lobste.rs/t/hardware.rss` | RSS 2.0 | `disk-ingest`, `tape-ops` |
| 12 | Lobsters tag `linux` | `https://lobste.rs/t/linux.rss` | same | `tape-ops`, `disk-ingest` |
| 13 | GitHub Releases — borg | `https://github.com/borgbackup/borg/releases.atom` | Atom, unauth, verified live [7] | `disk-ingest`, `media-ingest` |
| 14 | GitHub Releases — kopia | `https://github.com/kopia/kopia/releases.atom` | same | `disk-ingest` |
| 15 | GitHub Releases — velero | `https://github.com/velero-io/velero/releases.atom` | same (301 from vmware-tanzu) | `disk-ingest` |
| 16 | GitHub Releases — restic | `https://github.com/restic/restic/releases.atom` | same | `disk-ingest` |
| 17 | GitHub Discussions — borg | `https://github.com/borgbackup/borg/discussions.atom` | Atom, unauth [8] | `disk-ingest` |
| 18 | AWS Storage Blog | `https://aws.amazon.com/blogs/storage/feed/` | Atom, unauth | `tape-vault`, `vtl-cloud`, `monetize` |
| 19 | Tape Ark blog | `https://www.tapeark.com/feed/` | Atom, marketing-heavy — case studies only | `monetize` |

Skip-list: LinkedIn (no RSS), Twitter / X, Medium, Stack Overflow tags `cloud` / `aws` / `tape` / `ltfs` (404 or empty), Lobsters `storage` (404), Disqus threads (1,000 req/hr [9]), Firebase `topstories` until you budget per-ID fetches. Add sources only when the accept/reject ratio on the current set is healthy.

---

## 4. Four-Axis Triage Rubric

Without a rubric, the watcher drowns. The signal-to-noise ratio of a weekly Reddit `r/sysadmin` pull is roughly 1 in 30. The four axes below are the entire filter. Each axis is 0-3; the total is **0-12**, not 0-9.

| Axis | Score 0 | Score 1 | Score 2 | Score 3 |
|------|---------|---------|---------|---------|
| **Module-fit**: which of the 16 modules does the post touch? | none / off-topic | adjacent (mentions backup generically) | direct (names one module's keyword) | core (tool / library / pattern adoption) |
| **Actionability**: can the operator act on this in ≤ 30 min? | pure discussion | vague idea | links to a concrete tool | working code, library, or how-to |
| **Freshness**: how recent? | > 30 days | 8-30 days | 2-7 days | ≤ 24 hours |
| **Source-trust**: how trustworthy is the source? | personal blog, no comments | lobsters solo, reddit < 10 pts | reddit 10-100 pts, SO accepted answer, vendor blog | GitHub repo with releases, Stack Exchange tagged wiki, multi-thousand-upvote reddit |

A Discover candidate is any item that scores ≥ 7. Items scoring 5-6 are **Watch** (re-check next week). Items scoring ≤ 4 are **Skip** and feed the keyword blocklist (see Section 8). A free-LLM classifier assigns these scores; the rubric is also the prompt, so the operator only has to write it once.

The threshold of 7 is the parameter the operator tunes monthly. Start at 7. If the accept/reject ratio is < 30%, raise to 8. If > 70% and the queue feels under-filtered, drop to 6.

---

## 5. GitHub Actions Workflow

The pipeline is one workflow file, one Python script, and one `peter-evans/create-pull-request` step. In this repo the workflow is `.github/workflows/forum-watcher.yml` with `working-directory: forum-watcher`. In a dedicated `t2c-forum-watcher` repo, flatten to the tree in Section 14.

```yaml
# .github/workflows/forum-watcher.yml
name: forum-watcher

on:
  schedule:
    - cron: '0 9 * * 1'
      timezone: 'Australia/Sydney'
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  watch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install feedparser httpx pyyaml
      - env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python scripts/watch.py
      - uses: peter-evans/create-pull-request@v8
        with:
          commit-message: 'discoveries: weekly forum scan'
          title: 'Discoveries weekly forum scan'
          body: 'Auto-generated by forum-watcher. Check boxes to promote to Evaluate, then merge.'
          branch: discoveries/weekly
          delete-branch: true
          add-paths: |
            discoveries/*.md
            state/seen.json
```

**Schedule vs visibility.** GitHub documents the 60-day inactivity auto-disable for **public** repositories only [10]. A private repo does not get that public-repo pause, but free personal accounts have a separate, poorly documented failure: `schedule` on private repos may never fire unless the account is Pro. For a 1-person operator on the free plan, keep the watcher **public** (or pay for Pro) and add `gautamkrishnar/keepalive-workflow@v2` with `time_elapsed: 45` so the public-repo 60-day rule cannot silently kill the cron.

`peter-evans/create-pull-request@v8` only opens a PR when the workspace has changes. Zero new items → the step succeeds with no PR. That is correct [11]. Use `workflow_dispatch` to prove the workflow is alive.

---

## 6. Python Watcher Script

`forum-watcher/scripts/watch.py` is the classifier. Design choices that the draft got wrong and the kit now fixes:

1. **`import yaml` is required** (`pyyaml` is in the pip line; the draft script used `yaml.safe_load` without importing it).
2. **Algolia and Stack Exchange are JSON**, not RSS. `feedparser` on an Algolia body yields zero entries. Sources declare `kind: rss | algolia | se-api`.
3. **`seen` bootstrap.** `json.loads(text) if exists else "[]"` without wrapping the else in `json.loads` builds `set("[]")` — the characters `[` and `]`. The kit uses `[]`.
4. **`state/` must exist** before the first write.
5. **Per-source try/except** so one 404 does not fail the week.
6. **Heuristic fallback** when `GEMINI_API_KEY` is missing, so CI and first-run still write a markdown file.
7. **Score range is 0-12** (four axes × 0-3). Discover ≥ 7.

Dedupe is SHA-256 of URL in `state/seen.json`. The operator-facing verdict is only `discover | watch | skip`.

**Free-LLM model.** Gemini 2.5 **Flash** free tier is 10 RPM / 250 RPD, not 15 RPM / 1,000 RPD [12]. Those higher numbers are **Gemini 2.5 Flash-Lite**. The kit defaults to `gemini-2.5-flash-lite` because the job is trivial 4-axis JSON (95/5 cheap-tier work). Flash is the quality fallback. A weekly 30-50 call batch fits either quota. Sleep 60 seconds every 10 calls when an API key is present.

Fallback order if Flash-Lite is throttled: `gemini-2.5-flash` (10 RPM / 250 RPD), then Groq Llama 3.3 70B if you already have a key [12]. Do not send this workload to Claude Sonnet or Opus.

---

## 7. `sources.yaml`

A small YAML keeps the source list out of the Python file. Adding a source is one mapping. `module_hint` biases the classifier. Full file: `forum-watcher/sources.yaml`.

```yaml
- name: r/sysadmin
  url: https://www.reddit.com/r/sysadmin/.rss
  kind: rss
  module_hint: tape-ops, restore
  max_items: 25
- name: HN Algolia tape ops
  url: "https://hn.algolia.com/api/v1/search_by_date?query=tape%20OR%20ltfs%20OR%20lto&tags=story&hitsPerPage=20"
  kind: algolia
  module_hint: tape-ops
  max_items: 20
- name: SO API backup
  url: https://api.stackexchange.com/2.3/questions?order=desc&sort=activity&tagged=backup&site=stackoverflow&pagesize=15
  kind: se-api
  module_hint: disk-ingest, restore
  max_items: 15
```

---

## 8. Feedback Loop

When the operator opens the PR Monday morning, every `[ ]` checkbox is a Discover candidate. Checked = accept, unchecked = reject. After merge, record rows in `state/accept-reject.jsonl`:

```jsonl
{"date":"2026-09-08","verdict":"discover","module":"disk-ingest","score":8,"source":"r/BorgBackup","url":"...","action":"accept","reason":"new dedup chunker parameter worth testing"}
{"date":"2026-09-08","verdict":"discover","module":"tape-ops","score":7,"source":"r/sysadmin","url":"...","action":"reject","reason":"off-topic: RAID rebuild question"}
```

Once a month, compute accept/reject ratio per source. A source under 20% accept gets `max_items: 5` or is removed. A reject reason that recurs more than five times becomes a `blocklist.yaml` keyword, applied **before** the LLM call.

---

## 9. Failure Modes and Mitigations

| Failure | What we saw / expect | Mitigation |
|---|---|---|
| Reddit 403/429 from datacenter IPs | First `.rss` hit 200; later subs returned 429 in a back-to-back crawl on 2026-09-07 [2] | 1.5s delay between sources, custom User-Agent, demote after three dead weeks |
| Algolia empty hits | Narrow `numericFilters` windows go empty [4] | Drop the time filter; keep `tags=story`; Algolia has index lag |
| SO tag RSS 404 | `/feeds/tag/tape` and `/feeds/tag/ltfs` 404 on 2026-09-07 | Use `/feeds/tag/backup`, `/feeds/tag/lto`, plus SE API `tagged=backup` [6] |
| Lobsters tag 404 | `/t/storage.rss` 404; `/t/hardware.rss` 200 | Poll real tags only; 30s timeout; never fail the job on one source |
| Public-repo 60-day pause | Documented for public repos [10] | Keepalive action at 45 days, or a weekly merge of the discoveries PR |
| Free-plan private cron | `schedule` may not fire on free private repos | Public watcher repo, or GitHub Pro |
| Gemini quota | Flash-Lite 15 RPM / 1,000 RPD; Flash 10 / 250 [12] | Default Flash-Lite; heuristic classify if the key is missing |
| RSS schema drift | Atom vs RSS 2.0 | `feedparser` plus `.get()` defaults |

---

## 10. Optional Self-Host Upgrade

Default is GitHub-only and $0. If a VPS already exists:

- **Miniflux** — single Go binary, Postgres, smallest one-operator RSS reader [13].
- **Huginn** — MIT, agent/scrape/act; closest OSS equivalent to cron + classify [14].
- **n8n** — visual editor; Sustainable Use License, free for internal self-host [15].
- **Activepieces** — MIT n8n alternative, smaller connector set [16].

Stay on GitHub Actions unless the VPS is already paid for. Miniflux + Huginn buys a UI and 1-minute polling at VPS cost.

---

## 11. Monday 09:00 Australia/Sydney Path

1. Cron fires (`timezone: Australia/Sydney`). Actions fetches sources, dedupes, classifies, writes `discoveries/YYYY-MM-DD.md`, opens a PR if anything changed.
2. Operator opens the PR, checks Discover boxes worth Evaluate.
3. Optional comments: `evaluate`, `watch-next`, `low-priority`.
4. Merge. A follow-up action (out of scope for v1) can open Evaluate issues per checked item.
5. Evaluate work happens in the 5-stage loop from the prior turn.
6. Month end: tune threshold and `sources.yaml` from `accept-reject.jsonl`.

This watcher is a strict upstream feeder. It does not replace Evaluate / Integrate / Verify / Release.

---

## 12. Path Comparison

| Path | Setup | Monthly | LLM | Cadence | Best for |
|------|-------|---------|-----|---------|----------|
| **GitHub Actions + Flash-Lite (this design)** | ~1 hour | $0 | $0 | weekly | 1-person, no VPS |
| **Huginn + Miniflux on Hetzner** | ~4 hours | €4.15 | $0 (Ollama) or Gemini | 1-min | spare VPS |
| **n8n self-hosted** | ~3 hours | $0 (free tier) | $0 | event-driven | visual builder |
| **Activepieces cloud free** | ~30 min | $0 | $0 | event-driven | non-coder, 10-flow cap |
| **Manual Feedly / Inoreader** | 0 | $0 | $0 | manual | pre-MVP |

---

## 13. Cost Ceiling and 95/5 Routing

The job is under five Actions minutes per week (inside the 2,000-minute free tier). Flash-Lite at 30-50 calls/week is inside 1,000 RPD. Classification is Bucket A work from the tape-to-cloud routing rule: do not send it to Sonnet, Opus, or Fable [12].

Spend only if (a) Google removes the free tier or (b) you want hourly polling. Both are out of scope.

---

## 14. Deliverable File Map

Dedicated repo layout (flatten `forum-watcher/`):

```
t2c-forum-watcher/
├── .github/workflows/forum-watcher.yml
├── scripts/watch.py
├── sources.yaml
├── blocklist.yaml
├── discoveries/
└── state/
    ├── seen.json
    └── accept-reject.jsonl
```

This repository keeps the nested kit plus root workflows:

```
forum-watcher/          # copy-paste kit
  scripts/watch.py
  scripts/validate.py
  scripts/monthly.py
  sources.yaml
  free-test-tools.yaml
  discoveries/
  monthly/
  state/seen.json
  state/accept-reject.jsonl
.github/workflows/forum-watcher.yml
.github/workflows/mhvtl-validate.yml
.github/workflows/monthly-rollup.yml
forum_monitoring.md
vendor_forum_watcher_prompt.md
tests/test_forum_watcher.py
tests/test_mhvtl_validate.py
tests/test_monthly_rollup.py
```

---

## 15. Vendor-forum + mhvtl layer

This layer sits on the community watcher. It does not replace cron, SHA-256 dedupe, `create-pull-request@v8`, or keepalive.

**`--mode community|vendor|all`.** `sources.yaml` tags every row `group: community` or `group: vendor`. Weekly cron still runs `--mode all`. Manual dispatch can split the two so a Reddit 429 does not block GitHub release atoms.

**30 curl-verified vendor sources.** Telligent/Salesforce community RSS for Veritas, Cohesity, Rubrik, Veeam, and Commvault is 403/404/HTML as of 2026-09-07. Those URLs are not wired. Each vendor has a Reddit fallback (`r/netbackup`, `r/cohesity`, `r/rubrik`, `r/commvault`, `r/acronis`, `r/backupexec`, `r/dell`; `r/Veeam` already lives in the community list). Working extras: Veeam + Cohesity blogs, vendor GitHub `releases.atom`, ServerFault tags, SO tags `veeam`/`backupexec`/`emc`, two HN Algolia vendor queries, borg/velero/seaweedfs Discussions. Full DROP/KEEP table: `vendor_forum_watcher_prompt.md`.

**Vendor classifier block.** Vendor-tagged items append BEX / DD / CDM / CommCell / Helios / RCDM / IDPA / VONE / VBR so Flash-Lite does not treat jargon as off-topic. Community items do not get that block.

**mhvtl validation (Evaluate only).** `forum-watcher/scripts/validate.py` runs five tests: mhvtl `mtx` discovery, LTO-7 tar write-read + SHA-256, LTFS `mkltfs`, BorgBackup restore, SeaweedFS S3 round-trip. Each missing binary **skips**. Tape tests **never** run on GitHub-hosted runners (`sg` is absent; a silent fail would look like a pass). Workflow: `.github/workflows/mhvtl-validate.yml`, label `mhvtl-runner`, `runs-on: [self-hosted, linux, mhvtl]`. Docker Hub `adrianj/mhvtl` does not exist; mhvtl is a host kernel module (`markh794/mhvtl`).

**18 free tools.** `forum-watcher/free-test-tools.yaml` — mhvtl, mtx, mt-st, ltfs, Borg, Restic, Kopia, Duplicati, Duplicacy, SeaweedFS, Rclone, Velero, proxmox-backup-client, Wal-G, pgBackRest, etcdctl, VeeamZIP (windows-only), Cohesity-SDK-python.

**Monthly rollup.** First Monday 09:00 `Australia/Sydney` via `0 9 1-7 * 1` (GitHub has no `1#1`). `.github/workflows/monthly-rollup.yml` writes `forum-watcher/monthly/YYYY-MM.md` (top 10 sources, accept/reject ratio, community-shift flips, vendor major-version crossings, new tools) and opens a separate PR.

**Cost.** Same $0/month ceiling. Classification stays on Flash-Lite (not Flash's 250 RPD, not Sonnet/Opus). mhvtl has no LLM calls. Monthly rollup is local stats.

**Operator Monday path.** Weekly PR now has Community discover/watch and Vendor discover/watch. Check tape-ops / vtl-cloud / tape-duplicate boxes, merge, add label `mhvtl-runner` or `workflow_dispatch` mhvtl-validate on the self-hosted box. First Monday: separate monthly PR.

---

## 16. Out of Scope

**Real-time Slack/Discord/Teams.** Delivery is one weekly GitHub PR so attention stays in the Monday review. A `repository_dispatch` webhook is a later add.

**Comment-thread scraping.** Triage uses title + URL + 600-char summary. Comments are an extra 3-5 LLM calls per item and would press the Flash RPD cap.

---

## 17. References

[1] GitHub Changelog, "GitHub Actions: Late March 2026 updates," timezone support for scheduled workflows, 19 March 2026. https://github.blog/changelog/2026-03-19-github-actions-late-march-2026-updates/

[2] Reddit RSS Feeds vs the Reddit API (2026). https://www.redditapis.com/blogs/reddit-rss-feed-vs-api-2026

[3] Hacker News Firebase API. https://hacker-news.firebaseio.com/v0/

[4] HN Search API (Algolia). https://hn.algolia.com/api

[5] Gui Stetelle, Reddit API key difficulty in 2026. https://www.linkedin.com/posts/guistetelle_getting-a-reddit-api-key-in-2026-is-nearly-activity-7416441711553363968-cJB2

[6] Stack Exchange API 2.3. https://api.stackexchange.com/docs

[7] BorgBackup releases.atom — verified 2026-09-07, Release 2.0.0b24 / 2.0.0b23 / 1.4.5. https://github.com/borgbackup/borg/releases.atom

[8] GitHub Discussions Atom feeds. https://stackoverflow.com/questions/9542346/atom-rss-feeds-on-github-issues

[9] Disqus API basic rate limit. https://disqus.com/api/docs/

[10] GitHub Docs, scheduled workflows auto-disabled after 60 days **in a public repository**. https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows

[11] peter-evans/create-pull-request. https://github.com/peter-evans/create-pull-request

[12] Gemini API free-tier limits (Flash 10 RPM / 250 RPD; Flash-Lite 15 RPM / 1,000 RPD). https://ai.google.dev/gemini-api/docs/rate-limits and https://www.aifreeapi.com/en/posts/gemini-api-free-tier-rate-limits

[13] FreshRSS vs Miniflux, 2026. https://ossalt.com/guides/freshrss-vs-miniflux-2026

[14] Huginn vs n8n vs Activepieces, 2026. https://www.pistack.xyz/posts/huginn-vs-n8n-vs-activepieces-self-hosted-ifttt-alternatives-2026/

[15] Self-hosted automation tools, 2026. https://automationatlas.io/answers/best-self-hosted-automation-tools-2026/

[16] Open-source n8n alternatives, 2026. https://www.usecarly.com/blog/free-open-source-n8n-alternatives/
