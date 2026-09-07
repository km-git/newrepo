# Cursor Prompt — Enterprise-Vendor Forum Watcher + MHVTL Validation Loop

Operator copy of the 7-commit build prompt, **with live curl corrections from 2026-09-07**. The original job text follows the correction block. Implementation is already in this repo (`forum-watcher/`); this file is the durable prompt + the DROP table so a later operator does not re-wire dead Telligent URLs.

## Corrections vs the draft prompt (do not ignore)

| Draft claim | Live fact (2026-09-07) |
|-------------|-------------------------|
| Gemini Flash free tier is 15 RPM / 1,000 RPD / 30,000 calls/month | **Flash** is 10 RPM / 250 RPD. **Flash-Lite** (`gemini-2.5-flash-lite`) is 15 RPM / 1,000 RPD. Classification uses Flash-Lite. |
| MinIO CE archived 2026-02-14 | Archived **2026-04-25**. Default S3 stand-in is **SeaweedFS**. Smoke: `weed mini -dir=./data`, not `weed server -s3`. |
| `adrianj/mhvtl` Docker Hub image | **Object not found.** mhvtl is a host kernel module (`markh794/mhvtl`). Docker cannot load `mhvtl.ko` for you. |
| Cron `0 9 * * 1#1` for first Monday | GitHub POSIX has **no** `1#1`. Use `0 9 1-7 * 1` + `timezone: Australia/Sydney`. |
| Telligent RSS/API for Veritas, Cohesity, Rubrik, Veeam, Commvault | Almost all **403, 404, or HTML SPA**. Dropped. Reddit + GitHub + ServerFault + two vendor blogs are the working map. |
| `selectolax` HTML scrape | Not used. Hard rule: drop non-200 or non-XML/JSON. |
| 30 vendor sources from the listed Telligent URLs | **30 verified** replacements (see KEEP table). Do not add the dropped URLs back. |
| Monthly cron inside the same `on.schedule` as weekly watch | Separate workflow `monthly-rollup.yml`. Two crons on one workflow cannot tell which fired. |

### DROP (do not wire)

| Vendor / surface | URL | Result |
|------------------|-----|--------|
| Veritas community API | `https://www.veritas.com/api/community/v2/contents?...` | 403 |
| Veritas article.rss | `https://www.veritas.com/support/en_US/article.rss?product=NetBackup` | 403 |
| Cohesity developer feed | `https://developer.cohesity.com/feed.xml` | 404 |
| Cohesity community RSS/API | `https://community.cohesity.com/rss/...` | 200 HTML |
| Cohesity `dataprotect-mock-cookies` | GitHub | 404 |
| Rubrik community | `https://community.rubrik.com/` | DNS fail |
| Rubrik blog RSS | `https://www.rubrik.com/blog/rss.xml` | 403 |
| Rubrik docs RSS | `https://docs.rubrik.com/release-notes/rss.xml` | 200 HTML |
| Veeam community RSS/API | `https://community.veeam.com/rss/...` | 404 |
| Veeam KB RSS | `https://www.veeam.com/kb_search.html?rss=true` | 404 |
| Commvault Salesforce JSON | `https://community.commvault.com/sfc/...` | 404 |
| Commvault docs atom | `https://documentation.commvault.com/feed_atom.xml` | 404 |
| Dell PowerProtect RSS | community storage RSS | 404 |
| Dell support API | `https://www.dell.com/support/search/api/v1/articles?...` | 403 |
| Acronis community | `https://community.acronis.com/` | DNS fail |
| Acronis blog RSS | `https://www.acronis.com/blog/rss.xml` | 404 |
| Spiceworks backup.rss | | 404 |
| SO tags commvault, acronis, netbackup, rubrik, cohesity | `/feeds/tag/<tag>` | 404 |
| ServerFault tag rubrik | | 404 |
| `cvpysdk` discussions.atom | | 404 |
| `adrianj/mhvtl` | Docker Hub | 404 |

### KEEP (wired in `forum-watcher/sources.yaml`, `group: vendor`)

7 Reddit fallbacks (`r/netbackup`, `r/cohesity`, `r/rubrik`, `r/commvault`, `r/acronis`, `r/backupexec`, `r/dell`; `r/Veeam` stays in community to avoid duplicate SHA-256), Veeam blog, Cohesity blog, 8 GitHub release atoms (cvpysdk, terraform-provider-commvault, cohesity-powershell-module, rubrik python+powershell SDKs, dell csi-powerstore, dell csm, acronis-cyber-platform-python-examples), 5 ServerFault tags, 3 SO tags (`veeam`, `backupexec`, `emc`), 2 HN Algolia vendor queries, 3 GitHub Discussions (borg, velero, seaweedfs). **Total 30.**

---

# Original prompt (for replay / split shipping)

You are extending an existing `t2c-forum-watcher` GitHub-Actions pipeline (defined in `t2c-forum-watcher.yml`, `scripts/watch.py`, `sources.yaml`, `state/seen.json`, `state/accept-reject.jsonl`, `discoveries/`) that today monitors 23 free community sources for a 16-module tape-to-cloud migration tool. The 16 modules are: `audit`, `analytics`, `vtl-cloud`, `restore`, `disk-ingest`, `email-extract`, `email-migrate`, `tape-duplicate`, `media-ingest`, `tape-ops`, `tape-saas`, `tape-vault`, `destroy`, `llm-corpus`, `ml-enrich`, `monetize`. The 5-stage loop is: `Discover → Evaluate → Integrate → Validate → Compound`. The 95/5 model discipline routes trivial classification to Gemini Flash-Lite (free tier, 15 RPM, 1,000 RPD) and reserves expensive models only for Snowball/Tape-Gateway state machines, WORM policy, Temporal workflow, Nexus data model, and chain-of-custody posture.

Your job in this session: build the **vendor-forum + mhvtl validation** layer on top of the existing watcher. Do not rebuild the cron, the dedupe, the PR handoff, or the 5-stage loop. Do not introduce any new paid services, GPU/Ollama, or cloud APIs that cost money. Do not break the existing `peter-evans/create-pull-request@v8` PR handoff or the `gautamkrishnar/keepalive-workflow@v2` keepalive.

## Hard rules

1. **No new paid services.**
2. **No new dependencies beyond `feedparser`, `httpx`, `pyyaml`.** `selectolax` only if HTML scrape is required — this build dropped HTML sources instead.
3. **No GPU, no Ollama, no local LLM.**
4. **Do not break the existing PR handoff.**
5. **Dedupe across all sources** by SHA-256 of canonical URL. Drop `t.co` / `lnkd.in`.
6. **Every vendor source has a `module_hint`.**
7. **The 60-day inactivity pause still applies.** mhvtl and monthly workflows have their own keepalive.
8. **The mhvtl validation NEVER runs on a GitHub-hosted runner.** It needs kernel `sg`. Self-hosted `[self-hosted, linux, mhvtl]` or skip. Do not pretend Docker Hub `adrianj/mhvtl` exists.

## Seven commits (ship as one PR or split)

1. `feat(vendor-sources): add 30 vendor-forum sources to watcher`
2. `feat(vendor-classifier): add vendor-context block and mode flag`
3. `feat(mhvtl-validate): 5-test mhvtl smoke suite for tape/vtl/duplicate modules`
4. `feat(ci): add mhvtl validation workflow on-demand`
5. `feat(monthly): first-Monday rollup with source-quality stats`
6. `docs(test-tools): 18 free validation tools inventory`
7. `docs(forum-monitor): add vendor-forum + mhvtl layer section`

## Anti-patterns

- Do not route classification through Claude Sonnet or Opus.
- Do not add Slack/Discord webhooks.
- Do not store SHA-256 dedupe in GitHub Issues.
- Do not wire URL shorteners.
- Do not add the eight vendor Telligent URLs and call it done.
- Do not ship mhvtl on `ubuntu-latest`.
- Do not add paid vendor labs.
- Do not scrape comment threads.
