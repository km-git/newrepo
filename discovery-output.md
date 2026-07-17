# AU Micro-SaaS Discovery Portfolio

Research date: 17 July 2026  
Operator profile: AU-based, 1–2 people, 25+ years in IT services, AI consulting and tradie/NDIS familiarity.

## Read this first

- `Success %`, revenue, setup cost and build-day figures are screening estimates, not forecasts. Validate them with customer interviews and paid pilots.
- “No PII” is not realistic for quoting, booking, messaging or NDIS products. The practical constraint is to minimise and secure personal information and avoid health/sensitive information unless the product is deliberately designed for that regulatory burden.
- The 7–30 day estimate covers a narrow pilot MVP. API approval, production security, privacy review, app-marketplace approval and customer onboarding can extend launch time.
- Compliance products below are drafting, organising or reminder aids. They must not claim to provide legal, WHS, clinical, financial, NDIS eligibility or pricing advice.

## Ranked portfolio

| # | Name | Category | Target | Problem | Solution | Architect Model | Workhorse Models | Cursor Workflow | Stack | Build Days | Setup A$ | Pricing | Y1 Mid Rev A$ | Success % | First Customer | Risk |
|---|---|---|---|---|---|---|---|---|---|---:|---:|---|---:|---:|---|---|
| 1 | QuoteMate AI | Tradie/NDIS | Solo tradies | Quotes are completed late and jobs are lost | Turn voice notes and photos into a reviewed quote PDF | Fable 5 | Sonnet 5, Haiku 4.5 | Plan schema; build against 20 de-identified quotes | Next.js, Supabase, speech-to-text, Stripe | 14 | 800 | A$39/mo | 28K | 40 | Existing tradie client | ServiceM8/Tradify feature overlap |
| 2 | TradieDesk AI | AI Receptionist | Trade businesses | Missed after-hours calls lose jobs | Answer, capture job details and book a callback | Opus 4.8 | Sonnet 5, Luna | Model call states; test recorded scenarios before live pilot | Twilio, Node, Postgres | 21 | 1,500 | A$99/mo | 45K | Plumber in current network | Voice quality, consent and uptime |
| 3 | Tradie FollowUp | Tradie/NDIS | Trade SMBs | Sent quotes are not followed up | Consent-aware SMS/email sequences for open quotes | GPT-5.6 Sol | Luna, Haiku 4.5 | Specify state machine; test opt-out and idempotency | Next.js, Twilio, Stripe | 10 | 400 | A$29/mo | 22K | Electrician client | Spam Act and low ARPU |
| 4 | MissedCall TextBack | AI Receptionist | Local services | Callers immediately try a competitor | Transactional text-back with booking link and triage | Fable 5 | Haiku 4.5, Gemini Flash | Build one webhook; replay call fixtures | Twilio, Cloudflare Workers | 7 | 300 | A$25/mo | 18K | Local service client | Commodity feature; sender-ID rules |
| 5 | SiteSnap Docs | Tradie/NDIS | Builders and electricians | Job evidence is scattered through camera rolls | Photos and voice become dated job and handover records | Opus 4.8 | Sonnet 5 | Plan offline sync; test with representative photo sets | Expo, Supabase | 25 | 1,000 | A$45/mo | 30K | Builder in network | Mobile sync and personal data |
| 6 | Email-to-Job | AI Workflow | Trade administrators | Job requests disappear in shared inboxes | Extract job fields and push reviewed drafts to job software | Fable 5 | Luna, Haiku 4.5 | Build a 50-email fixture corpus before integration | Node, Gmail API, partner APIs | 12 | 200 | A$35/mo | 20K | ServiceM8-using client | Partner API dependence |
| 7 | Renewal Radar | AI Compliance | Trade SMBs | Licences, insurance and test dates lapse | User-entered renewal register with reminders | Opus 4.8 | Sonnet 5 | Model reminder states; test timezone and retry edges | Next.js, Postgres, email/SMS | 10 | 250 | A$29/mo | 19K | Insurance-broker referral | Must not interpret obligations |
| 8 | Review Responder | AI Tools SMB | Local SMBs | Reviews go unanswered | Draft on-brand replies for owner approval | Fable 5 | Haiku 4.5 | Build tone eval set; require approve-before-post | Node, Google Business Profile API | 8 | 150 | A$19/mo | 15K | Café or salon client | Easy to clone; platform overlap |
| 9 | TradeMargin | Analytics | Trade SMBs | Owners cannot see which jobs make money | Reconcile job and accounting data into margin views | Opus 4.8 | Sonnet 5 | Design reconciliation rules; test against hand calculations | Next.js, Xero API, Postgres | 20 | 500 | A$79/mo | 28K | Builder client | Poor source data |
| 10 | GBP Post Pilot | AI Content+SEO | Local SMBs | Business profiles become stale | Draft and schedule posts from approved photos and specials | Fable 5 | Haiku 4.5, Gemini Flash | Ship narrow scheduler; add API contract tests | Node, GBP API, cron | 8 | 150 | A$15/mo | 14K | Local SEO agency | Low ARPU and API changes |
| 11 | FormFlow | AI Workflow | Admin-heavy SMBs | Staff re-key PDF forms | Extract scans into a reviewed spreadsheet or CRM draft | GPT-5.6 Sol | Luna, Gemini Flash | Fixture-first extraction evals; human confirmation | Python, FastAPI, OCR | 12 | 250 | A$45/mo | 22K | Insurance broker | OCR edge cases |
| 12 | StrataMinutes | Micro-SaaS Vertical | Strata managers | Minutes take hours after meetings | Recording to structured draft minutes for review | Opus 4.8 | Sonnet 5 | Design template engine; evaluate names and motions | Next.js, speech-to-text, Supabase | 15 | 400 | A$69/mo | 26K | Strata referral | Accuracy and recording consent |
| 13 | InboxTriage SMB | AI Tools SMB | Shared inbox teams | Messages are routed manually | Classify, draft and route with explicit approval | GPT-5.6 Sol | Luna | Define taxonomy; test labelled emails and overrides | Node, Gmail/M365 APIs | 14 | 300 | A$49/mo | 24K | Accounting firm | Native-suite competition |
| 14 | Quote Rescue | Lead Gen | Online-quoting services | Visitors abandon quote forms | Detect abandonment and trigger consented follow-up | GPT-5.6 Sol | Haiku 4.5 | Test event, consent and suppression paths | JS snippet, Node, Twilio | 9 | 150 | A$35/mo | 15K | Existing web client | Needs traffic; Spam Act |
| 15 | BeforeAfter Sites | Service Platforms | Tradies | Great work is buried in social feeds | Turn approved job photos into a fast portfolio microsite | Fable 5 | Sonnet 5 | Template scaffold; visual regression and form tests | Astro, Supabase, Cloudflare | 12 | 250 | A$39/mo | 19K | Landscaper in network | Commoditised website builders |
| 16 | ClinicFront | AI Receptionist | Allied health clinics | Reception cannot handle routine calls | Booking and FAQ agent with hard clinical-advice refusals | Opus 4.8 | Sonnet 5 | Threat-model guardrails; refusal and escalation tests | Twilio, Cliniko API, Node | 24 | 1,500 | A$149/mo | 40K | Physio client | Health data and clinical boundary |
| 17 | PolicyDraft AU | AI Compliance | SMB owners | Internal policies are missing or stale | Versioned first-draft templates with review flags | Fable 5 | Sonnet 5 | Build clause library; require professional-review notice | Next.js, template DB | 14 | 300 | A$39/mo | 20K | Bookkeeper channel | Legal-advice perception |
| 18 | SOP Builder | AI Workflow | Growing SMBs | Processes remain in the owner’s head | Turn a screen recording into an editable SOP | GPT-5.6 Sol | Gemini Flash | Evaluate steps against short fixture recordings | Web app, vision API, object storage | 18 | 400 | A$29/mo | 18K | Franchise operator | Scribe/Loom competition |
| 19 | ProposalPolish | AI Tools SMB | Consultants and agencies | Proposals are slow and inconsistent | Generate reviewed drafts from a brief and approved proof points | Fable 5 | Sonnet 5 | Build claim-safe retrieval and style evals | Next.js, Supabase | 10 | 200 | A$35/mo | 17K | Consulting client | Generic output and false claims |
| 20 | NDIS Audit Organiser | AI Compliance | NDIS providers | Audit evidence is scattered | Organise uploaded evidence against user-selected checklists | Opus 4.8 | Sonnet 5 | Privacy design first; permissions and audit-log tests | Next.js, Supabase, object storage | 24 | 1,500 | A$129/mo | 30K | Provider contact | Sensitive data; not viable as “no PII” |
| 21 | LocalRank AU | AI Content+SEO | Local service SMBs | Little suburb-level search visibility | Create reviewed, differentiated local landing pages | GPT-5.6 Sol | Haiku 4.5, Gemini Flash | Add originality lint; publish only after approval | Astro, Cloudflare Pages | 12 | 200 | A$49/mo | 22K | Pest-control client | Thin-content search penalties |
| 22 | SupplierChase | Vertical AI Agents | Builders and wholesalers | Purchase-order ETAs require repeated chasing | Draft supplier follow-ups and parse replies into an ETA board | Fable 5 | Luna | Sandbox inbox; test approval, retries and thread matching | Node, Gmail API, Postgres | 16 | 300 | A$79/mo | 24K | Builder client | Supplier acceptance |
| 23 | TenderScout | Vertical AI Agents | Small construction firms | Tender packs are too long to triage | Extract deadlines, requirements and fit questions with citations | Opus 4.8 | Sonnet 5 | Schema-first extraction; answer with source page references | Python, document parsing, Postgres | 15 | 400 | A$99/mo | 26K | Commercial builder | Missed clauses; human review essential |
| 24 | ChurnPeek | Analytics | Micro-SaaS founders | Churn is noticed too late | Stripe event alerts and a manual save playbook | Fable 5 | Haiku 4.5 | Replay event fixtures; test duplicate/out-of-order events | Node, Stripe API, Postgres | 10 | 100 | A$29/mo | 15K | Indie founder community | Small niche and global competition |
| 25 | GrantMiner AU | Vertical AI Agents | AU SMBs | Relevant grants are missed | Match profiles to sourced grant notices; informational only | GPT-5.6 Sol | Gemini Flash | Crawl official sources; freshness and expiry tests | Python, Postgres | 14 | 200 | A$25/mo | 16K | Consulting client | Data freshness and advice boundary |
| 26 | PMFix Dispatch | Service Platforms | Property managers | Maintenance dispatch is phone tag | Structure tenant reports and route approved jobs to tradies | Opus 4.8 | Sonnet 5 | Model multi-party workflow; role-based E2E tests | Next.js, Supabase, Twilio | 28 | 1,200 | A$149/mo | 34K | PM via tradie network | Two-sided cold start and PII |
| 27 | CaseStudy Forge | AI Content+SEO | B2B SMBs | Customer stories are never written | Interview recording to approved case study and social drafts | Fable 5 | Sonnet 5 | Consent workflow; claim and attribution checks | Next.js, speech-to-text | 9 | 150 | A$99/case | 16K | Existing consulting clients | DIY substitute |
| 28 | AdSpend Sanity | Analytics | Small advertisers | Budget anomalies go unnoticed | Explain spend and conversion anomalies in plain language | GPT-5.6 Sol | Haiku 4.5 | Synthetic anomaly tests; never auto-change campaigns | Node, ad APIs, cron | 12 | 250 | A$39/mo | 17K | Agency contact | API access and false alarms |
| 29 | PR Digest Bot | Dev Tools | Small dev teams | Pull-request queues lose focus | Daily risk-ranked digest with source links | Fable 5 | Haiku 4.5 | Dogfood on own repos; snapshot and permission tests | GitHub App, Node | 8 | 100 | US$19/mo | 14K | Dev shop | GitHub-native overlap |
| 30 | SWMS Form Helper | AI Compliance | Commercial tradies | Repetitive form filling delays site work | Populate reviewed SWMS templates from job facts | Opus 4.8 | Sonnet 5 | Keep deterministic templates; test mandatory fields | Next.js, template DB | 12 | 300 | A$35/mo | 18K | Builder client | WHS liability perception |
| 31 | ApprovalRouter | AI Workflow | SMB operations teams | Approvals disappear in chat | Route spend, leave and quote approvals with audit history | GPT-5.6 Sol | Luna | State-machine tests; Slack/Teams sandbox | Node, Slack/Teams APIs | 13 | 200 | A$45/mo | 18K | Operations manager | Platform review delays |
| 32 | Listing Lift | AI Content+SEO | Real estate agents | Listing copy is repetitive | Generate fact-grounded copy variants from approved details | Fable 5 | Haiku 4.5 | Lock facts; evaluate unsupported claims | Next.js, vision API | 8 | 150 | A$29/mo | 14K | Local agent | Portal and CRM built-ins |
| 33 | IntentRadar | Lead Gen | B2B service firms | Public buying signals are missed | Monitor permitted sources and alert with cited context | GPT-5.6 Sol | Gemini Flash | Source-by-source adapters; dedupe and ToS review | Python, Postgres | 14 | 250 | A$69/mo | 20K | Own consulting pipeline | Scraping terms and fragility |
| 34 | MechanicMate | Micro-SaaS Vertical | Independent mechanics | Job cards are unclear to customers | Voice/photo notes to reviewed customer summaries | Fable 5 | Haiku 4.5 | Test against real de-identified job examples | PWA, Supabase, speech-to-text | 15 | 400 | A$39/mo | 18K | Local workshop | Low software appetite |
| 35 | API Doc Drift | Dev Tools | API-first teams | Documentation lags code | CI diff of OpenAPI and docs with suggested patch | GPT-5.6 Sol | Luna | Fixture repos; fail only on deterministic drift | GitHub Action, Node | 10 | 100 | US$29/mo | 15K | Dev shop | Narrow buyer pool |
| 36 | RecruitScreen Assist | Vertical AI Agents | Labour-hire firms | Recruiters manually compare every CV | Evidence table against explicit criteria; human decides | Opus 4.8 | Sonnet 5 | Bias and explainability evals; prohibit auto-rejection | Next.js, Postgres | 18 | 500 | A$149/mo | 26K | Labour-hire contact | Discrimination and privacy risk |
| 37 | SubbieBoard | Service Platforms | Builders and subcontractors | Availability is coordinated by phone | Simple availability board and introductions | Fable 5 | Sonnet 5 | Validate both sides before coding; role E2E tests | Next.js, Supabase, SMS | 22 | 800 | A$59/mo builders | 22K | Builder plus subbie contacts | Marketplace liquidity |
| 38 | AU Copy Localiser | AI Localisation | Agencies and resellers | US copy feels wrong to AU customers | Batch adapt spelling, units, idiom and flagged claims | GPT-5.6 Sol | Haiku 4.5, Gemini Flash | Curated before/after corpus; preserve facts | Node, web UI | 7 | 100 | A$19/mo | 12K | Agency contact | Thin moat |
| 39 | Meeting Actions AU | AI Tools SMB | SMB managers | Meetings produce no follow-through | Draft minutes and push approved actions to task tools | Fable 5 | Haiku 4.5 | Consent notice; transcript fixtures and integration tests | Node, speech-to-text, task APIs | 9 | 150 | A$25/mo | 14K | Existing client | Native meeting assistants |
| 40 | Salon Front Desk | AI Receptionist | Salons and groomers | Calls interrupt service delivery | Handle hours, pricing, booking and rescheduling | Opus 4.8 | Sonnet 5 | Reuse call core; domain scenario tests | Twilio, booking API, Node | 14 | 800 | A$89/mo | 24K | Local salon | Crowded category |
| 41 | AuditBook | Service Platforms | AI consultants | Audit delivery is ad hoc | Productised intake, evidence, report and roadmap portal | Fable 5 | Sonnet 5 | Encode report rubric; test export and tenant isolation | Next.js, Supabase, PDF | 16 | 300 | A$1.5K/audit | 25K | Existing consulting lead | Productised service, not pure SaaS |
| 42 | CRM Note Personaliser | AI Personalisation | B2B sales SMBs | Outreach ignores account history | Draft messages grounded in selected CRM notes | GPT-5.6 Sol | Luna | Retrieval evals; approval required; suppression lists | Node, HubSpot API | 10 | 150 | A$39/mo | 15K | Sales-led client | Spam Act and CRM-native AI |
| 43 | LogTriage CLI | Dev Tools | Lean engineering teams | Incident logs take too long to classify | Cluster errors, link commits and draft incident notes | Fable 5 | Haiku 4.5 | Dogfood; snapshot and redaction tests | Go CLI, LLM API | 12 | 50 | US$15/mo | 12K | Dev shop | Sensitive logs and incumbents |
| 44 | NDIS Roster Gap Alert | Tradie/NDIS | Small NDIS providers | Unfilled shifts are found too late | Flag gaps from roster exports and notify coordinators | Opus 4.8 | Sonnet 5 | Scheduling-only scope; simulated roster fixtures | Next.js, Postgres, SMS | 16 | 600 | A$99/mo | 32K | Provider contact | Worker/participant PII |
| 45 | Tourism Translator | AI Localisation | Regional tourism operators | Visitor material is English-only | Translate approved copy into editable print/web layouts | GPT-5.6 Sol | Gemini Flash | Native-speaker review workflow; layout tests | Node, translation API, PDF | 10 | 150 | A$29/mo or per document | 12K | Regional operator | Seasonal demand and translation errors |
| 46 | Industry Headline Swap | AI Personalisation | B2B SMB websites | One homepage serves every segment | Swap pre-approved copy by declared visitor segment | Fable 5 | Haiku 4.5 | Privacy-safe rules; A/B instrumentation | JS snippet, Cloudflare Workers | 11 | 150 | A$49/mo | 14K | Own site then client | Traffic needed to prove lift |
| 47 | CelebrantSuite | Micro-SaaS Vertical | Marriage celebrants | Ceremony drafts and admin repeat | Intake to editable script draft and checklist | Fable 5 | Haiku 4.5 | Template-first build; privacy and export tests | Next.js, Supabase | 12 | 200 | A$25/mo | 10K | Celebrant referral | Small market |
| 48 | RulePack Auditor | Dev Tools | AI-assisted dev teams | Agent rules conflict and bloat | Lint project-rule files and explain contradictions | GPT-5.6 Sol | Luna | Dogfood on rule fixtures; deterministic parser checks | Node CLI, GitHub Action | 8 | 50 | US$10/mo | 10K | AI-dev community | Niche and moving formats |
| 49 | App-String Localiser | AI Localisation | Indie app developers | Localisation is deferred as too expensive | CI translation drafts preserving placeholders | GPT-5.6 Sol | Gemini Flash | Round-trip placeholder and pluralisation tests | GitHub Action, Node | 9 | 50 | US$19/mo | 11K | Indie dev community | Lokalise and platform competition |
| 50 | PT Studio Check-ins | Micro-SaaS Vertical | Personal trainers | Client check-ins are inconsistent | Schedule questionnaires and draft trainer replies | Fable 5 | Haiku 4.5 | Avoid health recommendations; message-flow tests | Next.js, Twilio | 12 | 250 | A$29/mo | 12K | Gym owner | Health information and incumbents |
| 51 | PrivacyCheck Lite | AI Compliance | SMB website owners | Privacy notices and forms are often stale | Crawl site and produce a sourced gap checklist | Fable 5 | Haiku 4.5 | Deterministic scanner first; legal-review disclaimer | Node, Playwright | 9 | 100 | A$19/scan | 9K | Web agency partner | Free tools and legal-advice boundary |
| 52 | DirectoryBoost | Lead Gen | Niche service verticals | Buyers struggle to compare local suppliers | Curated directory with verified profiles and disclosed ads | GPT-5.6 Sol | Gemini Flash | Validate search demand; enrichment and claim checks | Astro, Postgres | 14 | 300 | A$49/mo featured | 12K | Firms already listed | SEO dependence and slow ramp |
| 53 | Proposal Personaliser | AI Personalisation | Agencies | Proposals ignore previous client context | Retrieve approved CRM/email facts into draft sections | Fable 5 | Luna | Citation and retrieval-quality evals | Node, CRM APIs | 12 | 200 | A$45/mo | 12K | Agency contact | Product overlap and privacy |
| 54 | Testimonial Wall | AI Personalisation | Service SMBs | Social proof is scattered | Consent-based collection and embeddable verified wall | GPT-5.6 Sol | Haiku 4.5 | Verify attribution; deletion and embed tests | Next.js, embeddable JS | 10 | 150 | A$25/mo | 13K | Web-design agency | ACL claims and fake reviews |
| 55 | Recurring Service Scheduler | Service Platforms | Lawn, pool and cleaning operators | Repeat visits and rebooking are manual | Simple recurring schedule, transactional reminders and rebook link | Opus 4.8 | Sonnet 5 | Calendar-state tests; separate service from marketing messages | Next.js, Postgres, SMS | 14 | 350 | A$39/mo | 18K | Local operator group | Calendar edge cases and messaging rules |

Category coverage: AI Tools SMB (4), Micro-SaaS Vertical (4), Vertical AI Agents (4), AI Content+SEO (4), Dev Tools (5), AI Workflow (4), Lead Gen (4), Analytics (4), Service Platforms (5), Tradie/NDIS (5), AI Receptionist (4), AI Compliance (5), AI Localisation (3), AI Personalisation (4).

## Top 10 to validate first

1. **QuoteMate AI — Fable 5:** interview five trade clients, collect 20 de-identified quotes, then build voice/photo input, editable line items, PDF export and acceptance tracking.
2. **TradieDesk AI — Opus 4.8:** map a bounded after-hours call state machine, test 30 recorded scenarios, then pilot on one overflow number.
3. **Tradie FollowUp — GPT-5.6 Sol:** implement quote states, consent records, opt-out suppression and two message templates; measure accepted quotes for one electrician.
4. **MissedCall TextBack — Fable 5:** ship the smallest Twilio webhook and booking-link flow, then compare recovered calls over a four-week pilot.
5. **SiteSnap Docs — Opus 4.8:** validate the handover-document template before building offline photo capture and sync.
6. **Email-to-Job — Fable 5:** establish a 50-email golden corpus, hit the agreed extraction threshold, then integrate one job platform.
7. **Renewal Radar — Opus 4.8:** pre-sell through one insurance broker, then build user-entered dates and reliable reminders without interpreting compliance.
8. **Review Responder — Fable 5:** secure a local-SEO reseller, build approve-before-post and test tone against real reviews.
9. **TradeMargin — Opus 4.8:** reconcile ten completed jobs by hand before automating Xero import and dashboarding.
10. **GBP Post Pilot — Fable 5:** pre-sell a white-label pilot to one local-SEO freelancer and ship only photo-to-draft, approval and scheduling.

The ranking deliberately favours an existing distribution advantage. A signed paid pilot is stronger evidence than any percentage in the table.

## Four-tier model routing

Model availability and pricing change; check Cursor’s current model page before budgeting.

| Tier | Models | Use | Target share |
|---|---|---|---:|
| 1 — Frontier architect | Fable 5, Opus 4.8, GPT-5.6 Sol | Architecture, data boundaries, security, auth/payments and a hard problem after cheaper attempts fail | 5–10% |
| 2 — Senior implementer | Sonnet 5, GPT-5.6 Terra, Composer | Multi-file features, integrations and substantive refactors | 25–30% |
| 3 — Workhorse | Haiku 4.5, GPT-5.6 Luna, Gemini Flash | CRUD, tests, docs, fixtures, configuration and simple fixes | 50–60% |
| 4 — Routine | Auto, Tab completion and the cheapest adequate option | Renames, formatting, boilerplate and small edits | 10–15% |

Routing rules:

1. Start a product with one Tier 1 session that writes acceptance criteria, data boundaries and a file-level plan.
2. Build from that specification with Tier 2/3 models.
3. Use Tier 1 again for security-critical decisions or after two evidence-backed cheaper attempts fail—not for routine edits.
4. Run tests and evals before changing model tier; a better test often supplies more value than a more expensive model.

## Token-saving cheat sheet

- Store acceptance criteria in `SPEC.md`; reference it instead of re-explaining the product.
- Give the agent only relevant files and a focused task.
- Create de-identified fixture corpora for every extraction or generation feature.
- Prefer a fresh conversation per independent task to avoid stale context.
- Let a single command such as `npm run check` report lint, types, tests and evals.
- Batch related small edits, but split unrelated work.
- Keep project rules short because always-applied instructions consume context.
- Check actual usage, cache and Max Mode pricing rather than extrapolating headline token rates.

## Continuous testing loop

1. **Plan:** write acceptance criteria, privacy boundary, failure modes and measurable eval thresholds.
2. **Build:** first create a failing test or eval fixture, then implement the narrowest vertical slice.
3. **Test:** run lint, types, unit/integration tests and the AI golden-set eval.
4. **Verify:** exercise the full user workflow with production-like inputs and inspect outputs, logs and permissions.
5. **Iterate:** convert every discovered failure into a regression test; repeat up to five evidence-driven cycles.
6. **Pilot:** release to one paid design partner with support and rollback paths.
7. **Decide:** expand only if activation, retained use and willingness to pay meet pre-written thresholds.

## Modern Cursor project-rule template

Rules guide agent behaviour; they do not force a model or sampling temperature. Select models in Cursor and keep repository rules in `.cursor/rules/*.mdc`.

```markdown
---
description: Core project conventions
alwaysApply: true
---

# Context
- Read SPEC.md before implementing a feature.
- Use the existing stack and patterns; do not introduce a framework without a written reason.

# Workflow
- Write or update tests before implementation.
- Run `npm run check` after each coherent change.
- For AI features, run the golden-set eval and report the score and failed cases.
- Never commit secrets, production personal data or `.env` files.

# Code
- Keep TypeScript strict.
- Prefer small pure functions and explicit boundaries.
- Add abstractions only after a second real use.
- Explain why in comments; do not narrate obvious code.

# Safety
- Treat auth, payments, tenant isolation and migrations as high risk.
- Use de-identified fixtures; never call live external APIs from tests.
- Require human approval before an AI-generated message, quote, policy or compliance document is sent.

# Handoff
- Summarise changed files, decisions, test commands and unresolved risks.
```

## Cursor power-user practices

1. Use a frontier model to produce a durable `SPEC.md`, then start fresh implementation sessions with a cheaper model.
2. End implementation tasks with explicit acceptance checks and require the agent to run them.
3. Extract auth, billing, tenancy, CI and eval harnesses into a maintained starter repository after the first validated product.
4. Pre-sell a paid pilot before building; distribution is the portfolio’s bottleneck.
5. Run one live product at a time until support and retention are understood.

## Current evidence and corrections

- Cursor’s official model documentation lists Fable 5 at US$10/M input and US$50/M output, Opus 4.8 at US$5/M and US$25/M, Sonnet 5 at US$3/M and US$15/M (with a temporary promotion), GPT-5.6 Sol at US$5/M and US$30/M, and GPT-5.6 Luna at US$1/M and US$6/M. Several require Max Mode on request-based plans; do not infer a fixed number of calls from a US$20 usage pool.
- NAB reported about 40% of Australian SMEs actively using AI in Q1 2026. The National AI Centre reported 43% across December 2025–February 2026, with content generation and analytics the most common uses and trust still a major barrier. These findings favour narrow, reviewable productivity products over opaque autonomous agents.
- Most businesses at or below A$3 million turnover remain exempt from the Privacy Act, but important exceptions include health-service providers and businesses trading in personal information. APP entities using personal information for significant automated decisions gain additional privacy-policy disclosure duties from 10 December 2026.
- Commercial email/SMS generally requires consent, sender identification and a functional unsubscribe honoured within five working days. Branded SMS sender IDs must be registered from 1 July 2026 or may appear as `Unverified`.
- NDIS Pricing Arrangements and Price Limits 2025–26 v1.1 took effect on 24 November 2025. Any product using support items or price limits needs a maintained authoritative data source and must not present itself as eligibility, pricing or compliance advice.

Sources:

1. [Cursor Models & Pricing](https://cursor.com/docs/models-and-pricing)
2. [NAB SME Business Insights: AI adoption](https://news.nab.com.au/content/dam/nab-news/documents/economics/sme_ai_adoptionrpt_2_benefits_from_ai.pdf)
3. [National AI Centre: AI adoption insights, Dec 2025–Feb 2026](https://www.ai.gov.au/news-and-insights/blog/ai-adoption-insights-december-2025-february-2026)
4. [OAIC: Small business and the Privacy Act](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/organisations/small-business)
5. [OAIC: Automated decision-making transparency guidance consultation](https://www.oaic.gov.au/engage-with-us/consultations/consultation-on-guidance-for-transparency-in-automated-decision-making)
6. [ACMA: Avoid sending spam](https://www.acma.gov.au/avoid-sending-spam)
7. [ACMA: SMS Sender ID Register](https://www.acma.gov.au/sms-sender-id-register)
8. [NDIS Pricing Arrangements and Price Limits 2025–26 v1.1](https://ndis.gov.au/media/8096/download?attachment=)
