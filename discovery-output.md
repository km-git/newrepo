# Discovery Output — Micro-SaaS / AI Tool / Vertical App Opportunity Map

**Prepared for:** 1–2 person Australian firm, 25+ years IT services experience, existing SMB / tradie / NDIS-provider client relationships.
**Constraints applied to every idea:** MVP buildable in 7–30 days; setup cost A$0–2K; ongoing run cost A$0–500/month; no storage of sensitive PII (health, biometric, financial account credentials — transient processing or metadata-only where relevant); no regulated advice (legal, financial, tax, clinical) — all generated documents are drafts for human review.

**Ranking method (global ranks 1–56):** weighted score of (a) pain intensity and frequency of the workflow, (b) existing budget for the problem, (c) reachability of the first customer from the firm's existing network, (d) build feasibility in 7–30 days, (e) defensibility/churn risk. Ranks are judgment-based estimates, not market data.

**Model-role convention (to avoid unverifiable claims):**
- *Architect model role* = how a frontier reasoning-class model is used **at design/build time** (schema design, prompt drafting, eval-set creation, edge-case analysis) — a process role, not a product claim.
- *Workhorse model role* = the **runtime** job given to a low-cost, fast model behind a provider-agnostic abstraction layer, so the specific vendor/model can be swapped as availability and pricing change. No specific model availability or pricing is asserted here; verify current provider terms before build.
- *Validation probability* = a subjective prior that 3+ paying customers can be reached within 90 days of launch. **These are estimates, not predictions of success.**
- Revenue figures are conservative Year-1 midpoints (partial-year ramp, modest churn), in AUD.

---

## Category 1: AI Tools SMB

### Rank 9 — ReviewReply Desk
- **Category:** AI Tools SMB
- **Target:** Local service SMBs with 20+ Google reviews/month (multi-location café groups, gyms, clinics front-desk)
- **Problem:** Owners ignore or badly answer reviews; response rate affects local ranking and bookings
- **Solution:** Dashboard that drafts on-brand replies to new Google/Facebook reviews for one-click approval
- **Architect model role:** Design-time: drafts tone-profile schema, reply templates, escalation rules; builds 100-review eval set
- **Workhorse model role:** Runtime: classifies sentiment and drafts replies from tone profile; human approves before posting
- **Cursor workflow:** Agent scaffolds Next.js + Google Business Profile API integration; repo-based prompt eval script; agent writes API mocks and tests
- **Stack:** Next.js, Supabase, GBP API, Stripe, hosted LLM API
- **Build days:** 10
- **Setup AUD:** $300 (domain, API verification, hosting)
- **Pricing AUD:** $49–99/month per location
- **Conservative Y1 midpoint revenue AUD:** $14,000
- **Validation probability:** ~45% (estimate)
- **First-customer route:** Existing IT-services clients with storefronts; local business chamber
- **Risk:** Platform API policy changes; feature absorbed by review platforms

### Rank 12 — QuoteChaser
- **Category:** AI Tools SMB
- **Target:** SMBs sending 20+ quotes/month (trades, printers, event hire)
- **Problem:** 40–60% of quotes never get a follow-up; revenue leaks silently
- **Solution:** Connects to email/Xero, detects unanswered quotes, drafts polite staged follow-ups for approval
- **Architect model role:** Design-time: designs follow-up cadence logic, objection-handling snippets, eval set of real quote threads (de-identified)
- **Workhorse model role:** Runtime: detects quote status from email threads and drafts follow-up text
- **Cursor workflow:** Agent builds Gmail/Microsoft Graph OAuth flow, thread-state machine, and unit tests; prompt iteration in repo
- **Stack:** Next.js, Supabase (metadata only), Gmail/Graph API, Xero API, Stripe
- **Build days:** 14
- **Setup AUD:** $400 (OAuth app verification, hosting)
- **Pricing AUD:** $59/month
- **Conservative Y1 midpoint revenue AUD:** $12,000
- **Validation probability:** ~45% (estimate)
- **First-customer route:** Tradie clients already on the firm's books; ServiceM8/Tradify user groups
- **Risk:** Email-provider app review friction; overlap with CRM follow-up features

### Rank 21 — TenderBrief
- **Category:** AI Tools SMB
- **Target:** SMBs bidding on council/government/commercial tenders (facilities, cleaning, IT, trades)
- **Problem:** Reading 80-page tender packs to decide go/no-go wastes days
- **Solution:** Upload tender pack → structured brief: scope, mandatory criteria, insurances required, red flags, deadline checklist (draft for review)
- **Architect model role:** Design-time: designs extraction schema (criteria, weightings, compliance clauses) and builds graded eval set from public tenders
- **Workhorse model role:** Runtime: chunked extraction and summary against the schema; documents processed transiently, not retained
- **Cursor workflow:** Agent scaffolds upload/parse pipeline (PDF→text), schema validation with Zod, eval harness against sample tenders
- **Stack:** Next.js, serverless functions, PDF parsing lib, hosted LLM API, Stripe
- **Build days:** 12
- **Setup AUD:** $200
- **Pricing AUD:** $79/month or $25/tender
- **Conservative Y1 midpoint revenue AUD:** $9,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Trades/facilities clients who already bid on council work
- **Risk:** Low frequency for small firms; accuracy expectations on complex packs

### Rank 24 — Meeting2Proposal
- **Category:** AI Tools SMB
- **Target:** IT consultants, MSPs, agencies (the firm's own peer network)
- **Problem:** Scoping-call notes take hours to turn into a professional proposal
- **Solution:** Paste call transcript/notes → structured proposal draft (scope, exclusions, timeline, pricing table placeholders)
- **Architect model role:** Design-time: builds proposal ontology, exclusion-clause library, and transcript→proposal eval pairs
- **Workhorse model role:** Runtime: maps transcript to proposal sections; flags ambiguities for the human to resolve
- **Cursor workflow:** Agent generates DOCX/PDF templating layer, section schema, and regression tests on sample transcripts
- **Stack:** Next.js, docx templating, Supabase, Stripe
- **Build days:** 10
- **Setup AUD:** $150
- **Pricing AUD:** $39/month
- **Conservative Y1 midpoint revenue AUD:** $7,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** MSP peer groups, the firm's own use as showcase
- **Risk:** Crowded generic-AI-writing space; must stay vertical (IT services templates) to differentiate

---

## Category 2: Micro-SaaS Vertical

### Rank 14 — DocChaser for Bookkeepers
- **Category:** Micro-SaaS Vertical
- **Target:** Solo bookkeepers/BAS agents managing 20–80 SMB clients
- **Problem:** Chasing clients for missing receipts/statements consumes hours monthly and delays lodgement work
- **Solution:** Per-client missing-document checklist with automated, escalating SMS/email reminders and a magic-link upload page (files passed through to their existing storage, not retained)
- **Architect model role:** Design-time: designs reminder-cadence logic and message tone variants; drafts checklist templates per entity type
- **Workhorse model role:** Runtime: classifies inbound replies ("already sent", "need more time") and updates checklist state
- **Cursor workflow:** Agent scaffolds multi-tenant checklist model, Twilio/SMTP integration, and end-to-end tests with mocked replies
- **Stack:** Next.js, Supabase, Twilio SMS, S3-compatible pass-through, Stripe
- **Build days:** 14
- **Setup AUD:** $400
- **Pricing AUD:** $49–99/month per practice
- **Conservative Y1 midpoint revenue AUD:** $13,000
- **Validation probability:** ~50% (estimate)
- **First-customer route:** The firm's own bookkeeper/accountant, then bookkeeper Facebook groups and ICB community
- **Risk:** Practice-management suites adding the feature; care needed to avoid storing financial docs (pass-through design)

### Rank 18 — FleetNudge
- **Category:** Micro-SaaS Vertical
- **Target:** Tradie businesses with 3–15 vehicles
- **Problem:** Rego, insurance, servicing and tool-calibration dates tracked in heads/spreadsheets; misses cause fines and downtime
- **Solution:** Simple asset register with SMS/email nudges, driver assignment, and a compliance snapshot for insurers
- **Architect model role:** Design-time: drafts asset taxonomies and reminder-policy defaults per trade
- **Workhorse model role:** Runtime: parses forwarded rego/insurance renewal emails into structured renewal records for confirmation
- **Cursor workflow:** Agent scaffolds CRUD + scheduling worker, generates seed data per trade, writes cron tests
- **Stack:** Next.js, Supabase, Twilio, Stripe
- **Build days:** 10
- **Setup AUD:** $300
- **Pricing AUD:** $29–79/month
- **Conservative Y1 midpoint revenue AUD:** $10,000
- **Validation probability:** ~45% (estimate)
- **First-customer route:** Existing tradie clients with multiple utes; local trade suppliers as channel
- **Risk:** Low willingness to pay if fleet is small; spreadsheet inertia

### Rank 26 — ToolTag
- **Category:** Micro-SaaS Vertical
- **Target:** Building/electrical crews of 5–25 with shared tools
- **Problem:** Tools walk off site; nobody knows who has what; replacement costs thousands per year
- **Solution:** QR-label check-in/check-out with photo condition log and "who has it" board
- **Architect model role:** Design-time: designs label/checkout flow and loss-report analytics
- **Workhorse model role:** Runtime: reads tool nameplates from photos to pre-fill asset records
- **Cursor workflow:** Agent builds PWA with camera/QR scanning, offline queue, and printable label sheets
- **Stack:** PWA (Next.js), Supabase, QR lib, Stripe
- **Build days:** 14
- **Setup AUD:** $350 (label printer for demos)
- **Pricing AUD:** $49/month per crew
- **Conservative Y1 midpoint revenue AUD:** $8,000
- **Validation probability:** ~40% (estimate)
- **First-customer route:** Builder clients; site-supervisor referrals
- **Risk:** Behaviour change on site is hard; hardware-adjacent competitors

### Rank 40 — ClubLedger
- **Category:** Micro-SaaS Vertical
- **Target:** Volunteer-run community sports clubs (footy, netball, cricket)
- **Problem:** Registration, fee tracking and gear deposits handled by burnt-out volunteers in spreadsheets
- **Solution:** Season setup wizard, member fee tracker with payment links, automated reminder runs
- **Architect model role:** Design-time: drafts season/fee data model and reminder copy variants
- **Workhorse model role:** Runtime: answers member fee questions from club-configured FAQ via email autoresponder
- **Cursor workflow:** Agent scaffolds multi-tenant club model, Stripe payment links, CSV import with tests
- **Stack:** Next.js, Supabase, Stripe, SMTP
- **Build days:** 16
- **Setup AUD:** $250
- **Pricing AUD:** $30–60/month seasonal
- **Conservative Y1 midpoint revenue AUD:** $5,000
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Own local club network
- **Risk:** Tiny budgets, seasonal churn, incumbent registration platforms

---

## Category 3: Vertical AI Agents

### Rank 16 — PriceBook Sync Agent
- **Category:** Vertical AI Agents
- **Target:** Builders/electricians/plumbers who quote from supplier price lists
- **Problem:** Supplier price PDFs change monthly; quotes silently use stale prices, eroding margin
- **Solution:** Agent ingests emailed supplier price-list PDFs, diffs against the user's price book, proposes line-item updates for approval
- **Architect model role:** Design-time: designs PDF-table extraction schema per supplier format and diff/approval workflow; builds accuracy eval set
- **Workhorse model role:** Runtime: table extraction and item matching (SKU/description fuzzy match), confidence-scored
- **Cursor workflow:** Agent builds parse→match→diff pipeline with golden-file tests per supplier sample
- **Stack:** Serverless pipeline, PDF table extraction, Supabase, ServiceM8/Tradify API push, Stripe
- **Build days:** 18
- **Setup AUD:** $400
- **Pricing AUD:** $79–149/month
- **Conservative Y1 midpoint revenue AUD:** $13,000
- **Validation probability:** ~40% (estimate)
- **First-customer route:** Existing builder clients; plumbing supply store noticeboards
- **Risk:** Long tail of messy PDF formats; extraction accuracy expectations

### Rank 22 — TenderWatch Agent
- **Category:** Vertical AI Agents
- **Target:** Trades/facilities SMBs wanting council and corporate tender leads
- **Problem:** Relevant tenders are scattered across portals; SMBs find them too late
- **Solution:** Agent monitors public tender feeds, filters by trade/region/value, emails a weekly digest with go/no-go one-liners
- **Architect model role:** Design-time: builds relevance rubric and digest format; creates labelled relevance eval set
- **Workhorse model role:** Runtime: classifies and summarises each tender listing against the client's profile
- **Cursor workflow:** Agent writes scrapers/feed readers with polite rate limits, relevance classifier harness, digest templating
- **Stack:** Python workers, Postgres, hosted LLM API, SMTP, Stripe
- **Build days:** 12
- **Setup AUD:** $200
- **Pricing AUD:** $49–99/month
- **Conservative Y1 midpoint revenue AUD:** $9,000
- **Validation probability:** ~40% (estimate)
- **First-customer route:** Same clients as TenderBrief; bundle the two
- **Risk:** Portal terms-of-use; digest fatigue if relevance is poor

### Rank 28 — NDIS Admin Inbox Agent
- **Category:** Vertical AI Agents
- **Target:** Small NDIS providers' admin staff (rostering/enquiry inboxes)
- **Problem:** Shared inboxes overflow with shift swaps, availability changes, enquiries; slow replies cost shifts
- **Solution:** Agent triages the inbox into categories, drafts replies from provider-approved templates; processes message content transiently and stores only category/status metadata (no participant health data retained)
- **Architect model role:** Design-time: designs category taxonomy, PII-minimisation rules, and template library with the provider
- **Workhorse model role:** Runtime: classification and template-filling on transient message content
- **Cursor workflow:** Agent builds Graph/Gmail integration, redaction layer with unit tests, category dashboard
- **Stack:** Next.js, Graph API, redaction middleware, Supabase (metadata only), Stripe
- **Build days:** 20
- **Setup AUD:** $500
- **Pricing AUD:** $149–249/month
- **Conservative Y1 midpoint revenue AUD:** $12,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Existing NDIS-provider IT clients
- **Risk:** Privacy sensitivity requires airtight transient-processing design; provider trust takes time

### Rank 44 — Warranty Claim Drafter
- **Category:** Vertical AI Agents
- **Target:** Appliance/equipment retailers and installers handling manufacturer warranty claims
- **Problem:** Claims require model/serial/fault narratives in each manufacturer's format; staff hate the paperwork
- **Solution:** Agent turns a photo of the nameplate + a voice note into a formatted claim draft per manufacturer template
- **Architect model role:** Design-time: builds per-manufacturer claim schemas and fault-narrative style guides
- **Workhorse model role:** Runtime: image nameplate extraction and narrative drafting into the schema
- **Cursor workflow:** Agent scaffolds mobile-first capture flow, template registry, and golden-file output tests
- **Stack:** PWA, vision-capable hosted model API, Supabase, Stripe
- **Build days:** 16
- **Setup AUD:** $300
- **Pricing AUD:** $59–99/month
- **Conservative Y1 midpoint revenue AUD:** $6,000
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Appliance installer contacts from trade network
- **Risk:** Narrow niche; per-manufacturer template maintenance

---

## Category 4: AI Content+SEO

### Rank 8 — AreaPages
- **Category:** AI Content+SEO
- **Target:** Tradies and local services wanting to rank in surrounding suburbs
- **Problem:** Service-area pages are the highest-ROI local SEO asset but cost $150+/page from agencies
- **Solution:** Generates unique, locally-grounded suburb × service pages (landmarks, council quirks, real job references supplied by the client) and publishes to their CMS; human review before publish
- **Architect model role:** Design-time: designs page schema, local-grounding data pipeline, and duplicate-content checks; builds quality rubric
- **Workhorse model role:** Runtime: drafts each page from structured local inputs; a checker pass scores against the rubric
- **Cursor workflow:** Agent builds suburb-data ingestion, WordPress/Webflow publish API, uniqueness linting, preview UI
- **Stack:** Next.js, Supabase, WordPress REST API, hosted LLM API, Stripe
- **Build days:** 12
- **Setup AUD:** $250
- **Pricing AUD:** $79–199/month tiered by pages
- **Conservative Y1 midpoint revenue AUD:** $18,000
- **Validation probability:** ~50% (estimate)
- **First-customer route:** Tradie clients whose sites the firm already manages
- **Risk:** Search-engine policy on scaled content — mitigated by real local grounding and human review

### Rank 19 — GBP Autopilot
- **Category:** AI Content+SEO
- **Target:** Local SMBs neglecting their Google Business Profile
- **Problem:** Regular GBP posts/photos correlate with local visibility, but owners never post
- **Solution:** Monthly content calendar of GBP posts drafted from the client's job photos and offers; approve-and-schedule
- **Architect model role:** Design-time: drafts post archetypes per industry and a monthly-mix planner
- **Workhorse model role:** Runtime: turns photo + one-line context into post copy variants
- **Cursor workflow:** Agent scaffolds GBP API scheduling, photo upload flow, approval queue with tests
- **Stack:** Next.js, GBP API, Supabase, Stripe
- **Build days:** 10
- **Setup AUD:** $250
- **Pricing AUD:** $39–79/month
- **Conservative Y1 midpoint revenue AUD:** $10,000
- **Validation probability:** ~45% (estimate)
- **First-customer route:** Bundle with ReviewReply Desk to same local clients
- **Risk:** GBP API access/policy changes

### Rank 23 — JobStory
- **Category:** AI Content+SEO
- **Target:** Builders, landscapers, renovators with photo-rich jobs
- **Problem:** Great before/after jobs never become website case studies or socials because writing is a chore
- **Solution:** Upload job photos + voice note → polished case study page, Instagram caption set, and GBP post in one pass (human review)
- **Architect model role:** Design-time: designs case-study narrative structure and multi-channel repurposing rules
- **Workhorse model role:** Runtime: drafts narrative from transcript + photo captions; formats per channel
- **Cursor workflow:** Agent builds media pipeline (resize, EXIF strip), transcript ingestion, multi-format templating with snapshot tests
- **Stack:** Next.js, object storage, speech-to-text API, hosted LLM API, Stripe
- **Build days:** 12
- **Setup AUD:** $300
- **Pricing AUD:** $49/month or $19/job
- **Conservative Y1 midpoint revenue AUD:** $8,500
- **Validation probability:** ~40% (estimate)
- **First-customer route:** Builder/landscaper clients; before-after content sells itself in demos
- **Risk:** Perceived as nice-to-have; usage-based engagement needed to hold retention

### Rank 31 — FAQ Miner
- **Category:** AI Content+SEO
- **Target:** SMBs with busy support/enquiry inboxes
- **Problem:** The same 30 questions get answered by email forever; none of it becomes searchable site content (increasingly important for AI-answer engines)
- **Solution:** Mines de-identified enquiry emails into an FAQ/answers hub with schema markup, published to their site after review
- **Architect model role:** Design-time: designs question-clustering approach, de-identification rules, and answer style guide
- **Workhorse model role:** Runtime: clusters questions, drafts canonical answers, generates FAQPage schema
- **Cursor workflow:** Agent builds mailbox export ingestion, clustering pipeline, CMS publishing, redaction tests
- **Stack:** Python pipeline, Next.js dashboard, WordPress API, Stripe
- **Build days:** 14
- **Setup AUD:** $250
- **Pricing AUD:** $59/month
- **Conservative Y1 midpoint revenue AUD:** $7,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Clients whose email the firm already administers (with consent)
- **Risk:** Email-content sensitivity; must de-identify rigorously before any model call

---

## Category 5: Dev Tools

### Rank 25 — Handover Auditor
- **Category:** Dev Tools
- **Target:** MSPs/consultancies inheriting undocumented codebases and systems from departed developers
- **Problem:** "Our developer left" engagements start with weeks of archaeology
- **Solution:** Point at a repo → structured handover report: architecture map, dependency risks, secrets-in-code flags, deploy-path reconstruction (draft for engineer review)
- **Architect model role:** Design-time: designs report ontology and severity rubric; builds eval repos with known issues
- **Workhorse model role:** Runtime: per-module summarisation and risk flagging over statically-extracted facts
- **Cursor workflow:** Agent builds AST/static-analysis extractors, report generator, and golden-report tests on fixture repos
- **Stack:** CLI + web report, tree-sitter/static analysis, hosted LLM API, Stripe
- **Build days:** 20
- **Setup AUD:** $200
- **Pricing AUD:** $99/month or $299/audit
- **Conservative Y1 midpoint revenue AUD:** $9,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** The firm's own rescue engagements; MSP peer referrals
- **Risk:** Each codebase is a snowflake; must scope to common stacks first

### Rank 37 — PromptGuard
- **Category:** Dev Tools
- **Target:** Small teams shipping LLM features without eval infrastructure
- **Problem:** Prompt tweaks silently regress behaviour; no CI signal
- **Solution:** Lightweight prompt regression harness: versioned prompts, graded test cases, CI pass/fail with diff reports
- **Architect model role:** Design-time: designs grading rubrics and test-case taxonomy; drafts starter eval packs per use case
- **Workhorse model role:** Runtime: acts as grader over candidate outputs (with human-audited calibration set)
- **Cursor workflow:** Agent builds CLI + GitHub Action, YAML test format, report renderer, self-tests
- **Stack:** TypeScript CLI, GitHub Actions, hosted LLM APIs, Stripe
- **Build days:** 14
- **Setup AUD:** $150
- **Pricing AUD:** $29–99/month
- **Conservative Y1 midpoint revenue AUD:** $6,000
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Dev communities; dogfood across all the firm's own products
- **Risk:** Fast-moving space with funded competitors; keep it niche-simple

### Rank 46 — ChangelogCourier
- **Category:** Dev Tools
- **Target:** Small software vendors/agencies maintaining client-facing APIs and sites
- **Problem:** Clients discover breaking changes the hard way; writing notices is always deferred
- **Solution:** Watches release notes/commits, drafts client-appropriate change notices (plain-English, impact-focused) for approval
- **Architect model role:** Design-time: designs audience-tiered notice templates and impact-classification rules
- **Workhorse model role:** Runtime: classifies change impact and drafts per-audience notices
- **Cursor workflow:** Agent builds GitHub webhook ingestion, notice templating, approval queue, mailer with tests
- **Stack:** Node workers, GitHub API, SMTP, Supabase, Stripe
- **Build days:** 10
- **Setup AUD:** $150
- **Pricing AUD:** $29–59/month
- **Conservative Y1 midpoint revenue AUD:** $4,500
- **Validation probability:** ~25% (estimate)
- **First-customer route:** Agency peers; the firm's own client comms
- **Risk:** Small budget line; often solved with a manual email

### Rank 48 — DriftSpotter
- **Category:** Dev Tools
- **Target:** Small dev shops managing many client environments
- **Problem:** Config drift between staging/prod and across client sites causes "works on mine" incidents
- **Solution:** Scheduled config/env snapshot diffing with plain-English drift reports and severity flags
- **Architect model role:** Design-time: designs drift taxonomy and severity heuristics
- **Workhorse model role:** Runtime: converts raw diffs into prioritised, readable drift summaries
- **Cursor workflow:** Agent builds collectors (env, DNS, package versions), diff engine, report UI, fixture-based tests
- **Stack:** Go/Node agents, Postgres, Next.js, Stripe
- **Build days:** 18
- **Setup AUD:** $200
- **Pricing AUD:** $49–99/month
- **Conservative Y1 midpoint revenue AUD:** $4,000
- **Validation probability:** ~25% (estimate)
- **First-customer route:** The firm's own managed clients as proving ground
- **Risk:** Agent-install friction; enterprise tools loom above the niche

---

## Category 6: AI Workflow

### Rank 3 — InvoiceChase Copilot
- **Category:** AI Workflow
- **Target:** Tradies and service SMBs on Xero/MYOB with chronic late payers
- **Problem:** SMBs carry tens of thousands in overdue invoices; chasing is awkward and inconsistent
- **Solution:** Reads aged-receivables via accounting API, runs an escalating, tone-calibrated reminder sequence (email/SMS) with owner approval gates; stores invoice metadata only
- **Architect model role:** Design-time: designs escalation ladder, tone matrix (mate→firm), dispute-detection rules, and reply-classification eval set
- **Workhorse model role:** Runtime: drafts reminders and classifies debtor replies (paid/dispute/promise-to-pay)
- **Cursor workflow:** Agent scaffolds Xero OAuth + webhook sync, sequence engine with state-machine tests, reply classifier harness
- **Stack:** Next.js, Supabase, Xero API, Twilio, Stripe
- **Build days:** 16
- **Setup AUD:** $500 (Xero app process, hosting)
- **Pricing AUD:** $59–129/month
- **Conservative Y1 midpoint revenue AUD:** $24,000
- **Validation probability:** ~60% (estimate)
- **First-customer route:** Existing tradie/SMB clients — nearly all have this pain; demo with their own aged-receivables report
- **Risk:** Xero app-store review timeline; must avoid anything resembling debt-collection regulation (reminders only, no collection activity)

### Rank 4 — Inbox2Job
- **Category:** AI Workflow
- **Target:** Tradies receiving job requests via email/website forms
- **Problem:** Enquiries arrive as unstructured emails; re-typing into job-management tools loses time and leads
- **Solution:** Parses enquiry emails/forms into structured job cards (name, address, job type, urgency, photos) and pushes into ServiceM8/Tradify/simPRO with one-tap confirm
- **Architect model role:** Design-time: designs job-card schema per trade and ambiguity-flagging rules; builds extraction eval set from sample enquiries
- **Workhorse model role:** Runtime: entity extraction from email text/attachments processed transiently
- **Cursor workflow:** Agent builds mail-in webhook, extraction pipeline with Zod validation, per-platform push adapters, fixture tests
- **Stack:** Serverless functions, Supabase (job metadata), ServiceM8/Tradify APIs, Stripe
- **Build days:** 12
- **Setup AUD:** $300
- **Pricing AUD:** $39–79/month
- **Conservative Y1 midpoint revenue AUD:** $18,000
- **Validation probability:** ~55% (estimate)
- **First-customer route:** Existing tradie clients on ServiceM8 (the firm can install it during routine IT visits)
- **Risk:** Platform API partnership requirements; extraction errors erode trust — keep confirm-before-create

### Rank 7 — SnapReport
- **Category:** AI Workflow
- **Target:** Trades and field services required to produce completion/inspection reports (electrical, pest, solar, property maintenance)
- **Problem:** Office evenings spent turning site photos and scribbles into client-ready reports
- **Solution:** Site photos + voice notes → structured, branded completion report PDF (sections, photo captions, recommendations) for review and send
- **Architect model role:** Design-time: designs per-trade report templates, caption style, and completeness checklists
- **Workhorse model role:** Runtime: photo captioning, transcript structuring, report assembly
- **Cursor workflow:** Agent builds mobile PWA capture, speech-to-text integration, PDF renderer, template snapshot tests
- **Stack:** PWA, object storage, speech-to-text + vision-capable model API, PDF generation, Stripe
- **Build days:** 16
- **Setup AUD:** $400
- **Pricing AUD:** $49–99/month
- **Conservative Y1 midpoint revenue AUD:** $16,000
- **Validation probability:** ~50% (estimate)
- **First-customer route:** Electrician and solar-installer clients; demo on one real job
- **Risk:** Job-management suites adding native report AI; photo handling must strip location EXIF by default

### Rank 17 — VoicemailTriage
- **Category:** AI Workflow
- **Target:** Solo tradies and small clinics whose voicemail is a black hole
- **Problem:** Voicemails go unheard for days; urgent jobs and cancellations are missed
- **Solution:** Transcribes voicemails, classifies urgency/intent, sends a summarised action list via SMS and drafts reply texts; audio discarded after processing
- **Architect model role:** Design-time: designs intent taxonomy (urgent job, quote, reschedule, spam) and summary format
- **Workhorse model role:** Runtime: transcription post-processing, intent classification, reply drafting
- **Cursor workflow:** Agent builds Twilio voicemail webhook, transcription pipeline, classification harness with labelled samples
- **Stack:** Twilio, speech-to-text API, serverless functions, Supabase (metadata), Stripe
- **Build days:** 8
- **Setup AUD:** $250
- **Pricing AUD:** $29–49/month
- **Conservative Y1 midpoint revenue AUD:** $11,000
- **Validation probability:** ~50% (estimate)
- **First-customer route:** Same tradie base; natural upsell path to full receptionist products
- **Risk:** Carrier voicemail-forwarding setup friction per customer

---

## Category 7: Lead Gen

### Rank 13 — DA Lead Miner
- **Category:** Lead Gen
- **Target:** Builders, pool builders, landscapers, electricians chasing renovation work
- **Problem:** Council development-application approvals are public, early buying signals — but scattered and unmonitored
- **Solution:** Monitors public DA/approval feeds for chosen councils, filters by work type, delivers weekly lead lists with property context (public data only)
- **Architect model role:** Design-time: designs DA-classification rubric (work type, likely trades needed) and lead-scoring model
- **Workhorse model role:** Runtime: classifies DA descriptions and drafts a one-line "why this is a lead for you"
- **Cursor workflow:** Agent writes per-council feed adapters, classifier eval harness, digest generator with tests
- **Stack:** Python scrapers/feeds, Postgres, hosted LLM API, SMTP, Stripe
- **Build days:** 14
- **Setup AUD:** $300
- **Pricing AUD:** $79–149/month per region
- **Conservative Y1 midpoint revenue AUD:** $14,000
- **Validation probability:** ~45% (estimate)
- **First-customer route:** Builder clients; one good lead pays for a year — easy demo
- **Risk:** Per-council feed variability and maintenance burden; respect site terms and robots

### Rank 20 — QualifyBot Widget
- **Category:** Lead Gen
- **Target:** Trades/services with website contact forms full of tyre-kickers
- **Problem:** Generic forms produce unqualified enquiries; owners waste hours on quotes that never convert
- **Solution:** Embeddable smart intake widget that asks adaptive qualifying questions (budget band, timeframe, photos) and scores the lead before it hits the inbox
- **Architect model role:** Design-time: designs per-trade qualification trees and scoring weights
- **Workhorse model role:** Runtime: adaptive follow-up question selection and lead-summary drafting
- **Cursor workflow:** Agent builds embeddable JS widget, config dashboard, scoring engine with unit tests
- **Stack:** Preact widget, Next.js dashboard, Supabase, Stripe
- **Build days:** 12
- **Setup AUD:** $200
- **Pricing AUD:** $39–79/month
- **Conservative Y1 midpoint revenue AUD:** $11,000
- **Validation probability:** ~45% (estimate)
- **First-customer route:** Install on tradie client sites the firm already hosts
- **Risk:** Form-builder incumbents; widget must be trivially easy to install

### Rank 27 — NewBiz Radar
- **Category:** Lead Gen
- **Target:** Accountants, IT providers, insurers, signage/fit-out firms selling to new businesses
- **Problem:** New business registrations are the best cold-outreach timing signal, but nobody watches them systematically
- **Solution:** Monitors public business-registration data by postcode/industry, enriches with public web presence, delivers weekly prospect lists
- **Architect model role:** Design-time: designs enrichment pipeline and fit-scoring rubric per subscriber vertical
- **Workhorse model role:** Runtime: drafts personalised outreach opener referencing public facts only
- **Cursor workflow:** Agent builds registry-data ingestion, enrichment workers, list export/CRM push with tests
- **Stack:** Python workers, Postgres, Next.js, Stripe
- **Build days:** 14
- **Setup AUD:** $350 (data access where applicable)
- **Pricing AUD:** $99–199/month
- **Conservative Y1 midpoint revenue AUD:** $10,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** The firm's accountant/bookkeeper contacts
- **Risk:** Data licensing/terms must be verified; spam-adjacent perception if outreach templates are lazy

### Rank 42 — WarmIntro Writer
- **Category:** Lead Gen
- **Target:** B2B service SMBs doing manual LinkedIn/email prospecting
- **Problem:** Personalising outreach at even small scale takes hours; generic blasts get ignored
- **Solution:** Given a prospect URL list, drafts genuinely specific openers from public website/news content, exported to their existing sending tool (no sending, no scraping behind logins)
- **Architect model role:** Design-time: designs "specificity rubric" and banned-cliché list; builds graded opener eval set
- **Workhorse model role:** Runtime: extracts public facts and drafts openers scored against the rubric
- **Cursor workflow:** Agent builds URL fetch/extract pipeline, rubric scorer, CSV in/out, rate-limit tests
- **Stack:** Node workers, headless fetch, hosted LLM API, Stripe
- **Build days:** 8
- **Setup AUD:** $150
- **Pricing AUD:** $29–59/month
- **Conservative Y1 midpoint revenue AUD:** $5,000
- **Validation probability:** ~30% (estimate)
- **First-customer route:** The firm's own outbound for its other products (dogfood), then peers
- **Risk:** Crowded space; platform anti-automation rules — stays compliant by drafting only

---

## Category 8: Analytics

### Rank 11 — WinRate Lens
- **Category:** Analytics
- **Target:** Tradies quoting through ServiceM8/Tradify/Xero
- **Problem:** Nobody knows which job types, suburbs or price bands they actually win — pricing stays gut-feel
- **Solution:** Pulls quote/invoice data via API, shows win rate by job type/size/suburb/response-time with plain-English monthly insights
- **Architect model role:** Design-time: designs insight taxonomy and "so what" narrative templates; validates metrics logic
- **Workhorse model role:** Runtime: turns computed metrics into a short plain-English monthly insight note (numbers computed deterministically, not by the model)
- **Cursor workflow:** Agent builds API sync jobs, metrics SQL with dbt-style tests, dashboard, narrative templating
- **Stack:** Next.js, Postgres, ServiceM8/Xero APIs, Stripe
- **Build days:** 16
- **Setup AUD:** $400
- **Pricing AUD:** $49–99/month
- **Conservative Y1 midpoint revenue AUD:** $14,000
- **Validation probability:** ~45% (estimate)
- **First-customer route:** Existing ServiceM8 tradie clients; show their own numbers in the demo
- **Risk:** Data quality in source systems; insight must beat "I already knew that"

### Rank 15 — JobProfit Board
- **Category:** Analytics
- **Target:** Builders and trades doing quoted (fixed-price) work
- **Problem:** Quoted-vs-actual hours and materials are rarely reconciled; losing jobs are repeated
- **Solution:** Joins quotes, timesheets and supplier invoices into per-job profit scorecards with variance alerts
- **Architect model role:** Design-time: designs job-costing data model and variance-alert thresholds per trade
- **Workhorse model role:** Runtime: matches messy supplier-invoice line items to jobs (confidence-scored, human-confirmed)
- **Cursor workflow:** Agent builds multi-source sync, matching engine with labelled test set, scorecard UI
- **Stack:** Next.js, Postgres, Xero + job-tool APIs, Stripe
- **Build days:** 20
- **Setup AUD:** $450
- **Pricing AUD:** $79–149/month
- **Conservative Y1 midpoint revenue AUD:** $13,000
- **Validation probability:** ~40% (estimate)
- **First-customer route:** Builder clients complaining about "busy but broke"
- **Risk:** Depends on decent timesheet discipline; longer build

### Rank 33 — SentimentBoard
- **Category:** Analytics
- **Target:** Multi-location SMBs (franchises, clinic groups, gyms)
- **Problem:** Reviews across locations/platforms are never compared; problem sites fester
- **Solution:** Aggregates reviews across platforms and locations; themes complaints, trends sentiment, flags outlier locations
- **Architect model role:** Design-time: designs complaint-theme taxonomy and alerting logic
- **Workhorse model role:** Runtime: theme extraction and monthly narrative per location
- **Cursor workflow:** Agent builds platform connectors, theming pipeline with eval set, comparison dashboard
- **Stack:** Next.js, Postgres, review platform APIs, Stripe
- **Build days:** 14
- **Setup AUD:** $300
- **Pricing AUD:** $99–199/month
- **Conservative Y1 midpoint revenue AUD:** $8,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Any multi-site client in the existing book; pairs with ReviewReply Desk
- **Risk:** API access limits; fewer multi-location prospects in a small network

### Rank 35 — Utilisation Pulse (NDIS)
- **Category:** Analytics
- **Target:** Small NDIS providers managing support-worker rosters
- **Problem:** Unfilled shifts and under-utilised workers directly cost revenue, but visibility is spreadsheet-grade
- **Solution:** Ingests roster exports (de-identified: worker codes, shift times, service codes only) and shows utilisation, cancellation patterns, and fill-time metrics
- **Architect model role:** Design-time: designs de-identification contract and utilisation metric definitions with provider input
- **Workhorse model role:** Runtime: drafts plain-English monthly operations summary from computed metrics
- **Cursor workflow:** Agent builds CSV-contract validator, metrics engine with tests, dashboard, PDF summary export
- **Stack:** Next.js, Postgres, Stripe
- **Build days:** 14
- **Setup AUD:** $300
- **Pricing AUD:** $99–199/month
- **Conservative Y1 midpoint revenue AUD:** $8,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Existing NDIS-provider IT clients
- **Risk:** Export formats vary by rostering tool; strict de-identification is non-negotiable

---

## Category 9: Service Platforms

### Rank 6 — SubbieCheck
- **Category:** Service Platforms
- **Target:** Builders and head contractors managing 5–50 subcontractors
- **Problem:** Tracking subbies' licences, insurances (public liability, workers comp), white cards and SWMS acknowledgements is a spreadsheet nightmare with real liability
- **Solution:** Portal where subbies upload their own compliance docs; AI parses expiry dates and coverage fields for human confirmation; builder gets a live compliance board and expiry alerts (business documents, not sensitive personal data)
- **Architect model role:** Design-time: designs document-type schemas (CoC fields, expiry, insurer) and confidence thresholds; builds parsing eval set from sample certificates
- **Workhorse model role:** Runtime: field extraction from uploaded certificates, always human-confirmed
- **Cursor workflow:** Agent scaffolds multi-tenant portal, upload/parse pipeline with golden-file tests, alerting worker, compliance dashboard
- **Stack:** Next.js, Supabase, object storage, vision-capable model API, Twilio/SMTP, Stripe
- **Build days:** 20
- **Setup AUD:** $500
- **Pricing AUD:** $99–249/month per builder
- **Conservative Y1 midpoint revenue AUD:** $20,000
- **Validation probability:** ~50% (estimate)
- **First-customer route:** Builder clients in the existing book; their liability exposure makes this a budgeted problem
- **Risk:** Must not present as compliance *advice* — it tracks documents and dates; parsing errors mitigated by human confirmation

### Rank 29 — BookNGo
- **Category:** Service Platforms
- **Target:** Mobile service operators (dog groomers, mobile mechanics, detailers)
- **Problem:** No-shows and phone-tag bookings kill route-based businesses
- **Solution:** Booking page with travel-zone slotting, card-on-file deposits, and automated SMS confirmations/reminders
- **Architect model role:** Design-time: designs travel-zone slotting logic and reminder cadences
- **Workhorse model role:** Runtime: interprets free-text reschedule replies into booking actions for confirmation
- **Cursor workflow:** Agent scaffolds booking engine, Stripe deposit flow, zone-based availability tests
- **Stack:** Next.js, Supabase, Stripe (deposits), Twilio
- **Build days:** 18
- **Setup AUD:** $350
- **Pricing AUD:** $39–79/month + payment fees pass-through
- **Conservative Y1 midpoint revenue AUD:** $9,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Local mobile operators; Facebook community groups
- **Risk:** Crowded booking-tool market — travel-zone niche is the wedge

### Rank 34 — PracticePortal
- **Category:** Service Platforms
- **Target:** Bookkeepers/accountants without client portals
- **Problem:** Client comms and document exchange happen over insecure email threads
- **Solution:** White-label portal: request lists, status tracking, secure pass-through file exchange (files relayed to the practice's own storage, not retained), e-sign requests via integration
- **Architect model role:** Design-time: designs request-list templates per engagement type
- **Workhorse model role:** Runtime: drafts client-facing status updates and reminder messages
- **Cursor workflow:** Agent scaffolds multi-tenant portal, pass-through storage adapter (Drive/OneDrive), integration tests
- **Stack:** Next.js, Supabase (metadata), Drive/OneDrive APIs, Stripe
- **Build days:** 20
- **Setup AUD:** $400
- **Pricing AUD:** $79–149/month per practice
- **Conservative Y1 midpoint revenue AUD:** $8,000
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Same bookkeeper network as DocChaser; bundle them
- **Risk:** Practice-suite incumbents; financial-document sensitivity handled by pass-through design

### Rank 38 — FixItBoard
- **Category:** Service Platforms
- **Target:** Small self-managing landlords and boutique property managers (5–100 doors)
- **Problem:** Maintenance requests arrive by text/call; tradie dispatch and status tracking is chaos
- **Solution:** Tenant-facing request form with photo upload, AI triage (urgency, trade needed), tradie dispatch links, and status timeline
- **Architect model role:** Design-time: designs triage taxonomy (urgency × trade) and dispatch-message templates
- **Workhorse model role:** Runtime: classifies requests from text+photo and drafts tradie work orders
- **Cursor workflow:** Agent scaffolds request pipeline, triage classifier harness, dispatch/SMS flows with tests
- **Stack:** Next.js, Supabase, Twilio, vision-capable model API, Stripe
- **Build days:** 18
- **Setup AUD:** $400
- **Pricing AUD:** $49–149/month by door count
- **Conservative Y1 midpoint revenue AUD:** $7,500
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Landlords within the existing client/personal network; tradie clients as the dispatch side
- **Risk:** PM software incumbents; two-sided coordination adds support load

---

## Category 10: Tradie/NDIS

### Rank 2 — SWMS Studio
- **Category:** Tradie/NDIS
- **Target:** Tradies and small builders needing Safe Work Method Statements per job/site
- **Problem:** SWMS are mandatory for high-risk construction work; tradies either pay $50–100 per template, recycle stale ones, or lose work — painful, frequent, budgeted
- **Solution:** Generates job-specific SWMS drafts from a guided Q&A (trade, tasks, site conditions), building on the business's own approved control library; clearly positioned as drafts the PCBU must review and sign off — a documentation tool, not safety advice
- **Architect model role:** Design-time: designs hazard/control ontology per trade from public regulator guidance, drafting templates, and a reviewer checklist; builds eval set scored by a safety-literate human
- **Workhorse model role:** Runtime: maps job description to relevant hazard/control blocks and drafts the document for review
- **Cursor workflow:** Agent scaffolds guided form, control-library data model, DOCX/PDF renderer, snapshot tests per trade template
- **Stack:** Next.js, Supabase, docx/PDF generation, hosted LLM API, Stripe
- **Build days:** 14
- **Setup AUD:** $500 (template review by a WHS consultant)
- **Pricing AUD:** $29–69/month
- **Conservative Y1 midpoint revenue AUD:** $26,000
- **Validation probability:** ~60% (estimate)
- **First-customer route:** Existing tradie clients — most already buy SWMS templates; builder clients can push it to their subbies
- **Risk:** Must stay firmly on the "drafting tool, you review and own it" side of the line; competitor template shops

### Rank 5 — AuditReady (NDIS)
- **Category:** Tradie/NDIS
- **Target:** Small registered NDIS providers facing recertification audits
- **Problem:** Audit prep is a scramble across policies, staff credentials (clearances, training expiry), and evidence artefacts; failed audits threaten registration — highly budgeted pain
- **Solution:** Audit-readiness workspace: practice-standards checklist mapped to the provider's evidence items, staff-credential expiry tracking (dates and document references only, no participant data), gap report before the auditor arrives
- **Architect model role:** Design-time: structures the publicly available practice-standards indicators into a checklist/evidence data model; drafts gap-report language (informational, not consulting advice)
- **Workhorse model role:** Runtime: matches uploaded evidence titles/metadata to checklist indicators and drafts gap summaries for human review
- **Cursor workflow:** Agent scaffolds checklist engine, evidence linking, expiry alert worker, gap-report PDF with tests
- **Stack:** Next.js, Supabase, object storage (provider's own bucket option), Stripe
- **Build days:** 18
- **Setup AUD:** $600 (checklist validation with an NDIS consultant)
- **Pricing AUD:** $99–249/month
- **Conservative Y1 midpoint revenue AUD:** $19,000
- **Validation probability:** ~50% (estimate)
- **First-customer route:** Existing NDIS-provider IT clients; NDIS provider Facebook/LinkedIn groups
- **Risk:** Position as organisation tool, not compliance advice; standards updates require checklist maintenance

### Rank 30 — ShiftNote Helper
- **Category:** Tradie/NDIS
- **Target:** NDIS support workers and coordinators writing daily shift notes
- **Problem:** Notes are rushed, inconsistent, and audit-weak; workers hate writing them after long shifts
- **Solution:** Voice note → structured, objective shift-note draft in the provider's required format, delivered straight into their existing CRM/clipboard; fully transient processing — nothing stored by the service
- **Architect model role:** Design-time: designs note structure (objective language, goal-linked format) with provider input and builds a quality rubric
- **Workhorse model role:** Runtime: transcription cleanup and restructuring on transient content; output handed off immediately
- **Cursor workflow:** Agent builds PWA voice capture, stateless processing pipeline, clipboard/CRM handoff, redaction tests
- **Stack:** PWA, speech-to-text API, stateless serverless functions, Stripe
- **Build days:** 12
- **Setup AUD:** $300
- **Pricing AUD:** $10–15/worker/month
- **Conservative Y1 midpoint revenue AUD:** $9,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Existing NDIS-provider clients rolling it to their workers
- **Risk:** Content is inherently sensitive — the zero-retention architecture must be verifiable and clearly communicated; provider CRMs adding native dictation

### Rank 32 — QuickQuote Builder
- **Category:** Tradie/NDIS
- **Target:** Solo tradies quoting from memory and losing margin
- **Problem:** Quoting takes evenings; inconsistent pricing across similar jobs
- **Solution:** Mobile quote builder with the tradie's own price book, assembly presets ("standard bathroom rewire"), photo attachments, and e-acceptance
- **Architect model role:** Design-time: designs per-trade assembly/preset structures and margin guardrails
- **Workhorse model role:** Runtime: suggests line items from a job description against the price book (suggestions only)
- **Cursor workflow:** Agent scaffolds PWA quote flow, price-book model, PDF/e-accept flow, calculation tests
- **Stack:** PWA (Next.js), Supabase, PDF generation, Stripe
- **Build days:** 16
- **Setup AUD:** $300
- **Pricing AUD:** $29–59/month
- **Conservative Y1 midpoint revenue AUD:** $8,500
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Tradie clients not yet on ServiceM8/Tradify (too heavy for them)
- **Risk:** Squeezed between free tools and full job-management suites; PriceBook Sync Agent is the differentiating bundle

---

## Category 11: AI Receptionist

### Rank 1 — MissedCall Rescue
- **Category:** AI Receptionist
- **Target:** Tradies and appointment businesses who miss 30–60% of inbound calls while on the tools
- **Problem:** A missed call is usually a lost job — callers ring the next tradie within minutes; pain is daily, obvious, and directly tied to revenue
- **Solution:** Instantly texts back missed callers, runs a short AI-guided SMS qualification (job type, suburb, urgency, photos), and delivers a ready-to-call lead card; no sensitive data stored — job details and contact number only, with retention controls
- **Architect model role:** Design-time: designs per-trade qualification scripts, escalation rules (emergency → call now), and a conversation eval set graded for tone and completeness
- **Workhorse model role:** Runtime: conducts the SMS dialogue within the scripted guardrails and summarises into the lead card
- **Cursor workflow:** Agent scaffolds Twilio missed-call webhook + SMS state machine, guardrail tests for off-script inputs, lead-card UI, onboarding wizard
- **Stack:** Twilio, serverless functions, Supabase, Next.js dashboard, Stripe
- **Build days:** 10
- **Setup AUD:** $400 (numbers, hosting, brand)
- **Pricing AUD:** $49–99/month + SMS usage
- **Conservative Y1 midpoint revenue AUD:** $28,000
- **Validation probability:** ~65% (estimate)
- **First-customer route:** Existing tradie clients — the firm can demo by calling their line during a site visit; trade suppliers and buy-swap-sell groups next
- **Risk:** US-style competitors entering AU; carrier/SMS compliance (opt-out handling) must be built in from day one

### Rank 10 — AfterHours Voice Agent
- **Category:** AI Receptionist
- **Target:** Emergency-capable trades (plumbers, electricians, locksmiths) and clinics after 5pm
- **Problem:** After-hours calls are either lost or interrupt dinner; answering services cost $2–4/call with poor quality
- **Solution:** Voice agent answers after-hours, captures job details, applies the business's emergency criteria, and either books a callback slot or escalates genuine emergencies by SMS to the on-call person; call recordings auto-purged on a short cycle
- **Architect model role:** Design-time: designs call flows, emergency-triage decision tree (business-defined criteria, not advice), failure-mode handling (fallback to human voicemail), and a call-quality eval rubric
- **Workhorse model role:** Runtime: real-time conversation within the flow via a telephony-AI platform, plus post-call summarisation
- **Cursor workflow:** Agent builds telephony-platform integration, flow configuration as versioned code, simulated-call test harness, escalation worker
- **Stack:** Telephony-AI platform (verify current vendor terms), Twilio, serverless functions, Supabase, Stripe
- **Build days:** 18
- **Setup AUD:** $700 (platform setup, test numbers)
- **Pricing AUD:** $149–299/month + usage
- **Conservative Y1 midpoint revenue AUD:** $17,000
- **Validation probability:** ~40% (estimate)
- **First-customer route:** Plumber/electrician clients already paying human answering services — direct cost-replacement pitch
- **Risk:** Voice reliability expectations are high; usage costs must be monitored against the $500/month run-cost cap per early deployment

### Rank 36 — ReBooker
- **Category:** AI Receptionist
- **Target:** Allied-health and personal-services clinics with no-show problems
- **Problem:** No-shows and unfilled cancellations cost clinics hundreds per week; front desk can't chase everyone
- **Solution:** Automated reminder + easy-reschedule agent over SMS; fills cancellations from a standby list; stores appointment times and first names only — no clinical information
- **Architect model role:** Design-time: designs reminder cadence, waitlist-fill logic, and reply-interpretation rules
- **Workhorse model role:** Runtime: interprets free-text replies ("can't do Tues arvo") into reschedule actions for confirmation
- **Cursor workflow:** Agent builds calendar-integration sync, SMS dialogue state machine, waitlist engine, reply-parsing tests
- **Stack:** Twilio, calendar APIs, Supabase, Next.js, Stripe
- **Build days:** 16
- **Setup AUD:** $400
- **Pricing AUD:** $79–149/month
- **Conservative Y1 midpoint revenue AUD:** $8,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Local physio/chiro/beauty businesses in the client network
- **Risk:** Practice-management systems bundle reminders; differentiation is the standby-fill intelligence

### Rank 39 — PriceBook Chat
- **Category:** AI Receptionist
- **Target:** Trades/services fielding constant "roughly how much for…?" enquiries
- **Problem:** Ballpark-price questions eat phone time; refusing to answer loses leads
- **Solution:** Website chat that answers with the business's own configured price ranges and caveats, then captures the lead; never invents prices — answers only from the configured price book
- **Architect model role:** Design-time: designs price-book schema, guardrails against off-book answers, and caveat language
- **Workhorse model role:** Runtime: retrieval-grounded chat over the price book with strict refusal outside it
- **Cursor workflow:** Agent builds embeddable chat widget, retrieval layer, guardrail red-team test suite, lead capture flow
- **Stack:** Preact widget, vector/keyword retrieval, serverless functions, Supabase, Stripe
- **Build days:** 12
- **Setup AUD:** $250
- **Pricing AUD:** $39–79/month
- **Conservative Y1 midpoint revenue AUD:** $6,500
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Install on client sites the firm hosts; pairs with QualifyBot
- **Risk:** Off-book hallucination would be brand-damaging — guardrail testing is the product

---

## Category 12: AI Compliance

### Rank 41 — PolicyPack Drafter (NDIS)
- **Category:** AI Compliance
- **Target:** Sole-trader and small NDIS providers preparing registration/renewal documentation
- **Problem:** Providers pay consultants $3–8K for policy packs that are largely structured boilerplate needing business-specific tailoring
- **Solution:** Guided intake → tailored draft policy documents mapped to publicly available practice standards, explicitly requiring provider review and consultant/auditor sign-off; a drafting accelerator, not compliance advice
- **Architect model role:** Design-time: structures public standards into document templates and tailoring questions; drafts review-checklist companion
- **Workhorse model role:** Runtime: merges intake answers into templates and flags sections needing professional review
- **Cursor workflow:** Agent builds intake wizard, template merge engine, DOCX export, diff-vs-template tests
- **Stack:** Next.js, Supabase, docx templating, Stripe
- **Build days:** 14
- **Setup AUD:** $800 (template review by an NDIS consultant — worth it)
- **Pricing AUD:** $299–499 one-off + $29/month updates
- **Conservative Y1 midpoint revenue AUD:** $9,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** NDIS provider startup groups; consultant partnerships (they review, tool drafts)
- **Risk:** The advice line must be respected scrupulously; consultants may see it as competition — partner instead

### Rank 45 — CertVault
- **Category:** AI Compliance
- **Target:** Any SMB juggling expiring business credentials (licences, insurances, certifications, vehicle inductions)
- **Problem:** Expired certificates surface at the worst moment — lost contracts, failed site inductions
- **Solution:** Drop documents in; AI extracts type/expiry/coverage for human confirmation; calendarised alerts and a shareable "currently compliant" summary link
- **Architect model role:** Design-time: designs document-type schemas and extraction confidence policy
- **Workhorse model role:** Runtime: field extraction from uploaded certificates, human-confirmed
- **Cursor workflow:** Agent builds upload/parse pipeline with golden-file tests, alert worker, share-link view
- **Stack:** Next.js, Supabase, object storage, vision-capable model API, Stripe
- **Build days:** 10
- **Setup AUD:** $250
- **Pricing AUD:** $19–49/month
- **Conservative Y1 midpoint revenue AUD:** $6,000
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Every existing client has this problem; simplest cross-sell in the portfolio
- **Risk:** Low price point needs volume; overlaps SubbieCheck (this is the single-business version — deliberate ladder)

### Rank 47 — ToolboxTalk Logger
- **Category:** AI Compliance
- **Target:** Trade crews required to run and document toolbox talks / safety meetings
- **Problem:** Talks happen but records don't; missing documentation hurts in incident reviews
- **Solution:** Foreman records a 2-minute voice summary + attendee tap-list → formatted talk record with topic, attendees, and actions, archived and exportable
- **Architect model role:** Design-time: designs record format aligned to common WHS documentation expectations and topic library
- **Workhorse model role:** Runtime: structures the voice summary into the record format
- **Cursor workflow:** Agent builds PWA capture, attendee roster model, PDF export, archive search with tests
- **Stack:** PWA, speech-to-text API, Supabase, Stripe
- **Build days:** 10
- **Setup AUD:** $250
- **Pricing AUD:** $29–49/month per crew
- **Conservative Y1 midpoint revenue AUD:** $5,000
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Builder clients; bundles naturally with SWMS Studio
- **Risk:** Documentation tool positioning (not WHS advice); depends on foreman habit formation

### Rank 49 — SiteScan Privacy Checker
- **Category:** AI Compliance
- **Target:** SMB website owners unaware of privacy-policy and consent gaps
- **Problem:** Sites collect form data and run trackers without adequate disclosure; awareness is rising with AU privacy reform coverage
- **Solution:** Scans a site for forms, trackers and cookie behaviour; produces a plain-English findings report and draft disclosure text flagged for professional review — informational, not legal advice
- **Architect model role:** Design-time: designs findings taxonomy and careful non-advice report language
- **Workhorse model role:** Runtime: summarises detected technical facts into the findings report
- **Cursor workflow:** Agent builds headless-browser scanner, tracker fingerprint library, report renderer with fixture-site tests
- **Stack:** Playwright workers, Next.js, Stripe
- **Build days:** 12
- **Setup AUD:** $200
- **Pricing AUD:** $49/scan or $19/month monitoring
- **Conservative Y1 midpoint revenue AUD:** $4,500
- **Validation probability:** ~25% (estimate)
- **First-customer route:** Run free scans for existing clients as conversation starter
- **Risk:** Must never drift into legal advice; willingness to pay unproven

---

## Category 13: AI Localisation

### Rank 43 — EasyRead Converter
- **Category:** AI Localisation
- **Target:** NDIS providers, councils, and community organisations needing accessible communications
- **Problem:** Easy English / plain-language versions of letters, service agreements and notices are required for accessibility but expensive to produce manually
- **Solution:** Converts documents into Easy English drafts (short sentences, defined terms, image-placeholder suggestions) following published accessibility style guides; human review required before use; documents processed transiently
- **Architect model role:** Design-time: encodes public Easy English style guides into conversion rules and builds a reviewer rubric with an accessibility consultant
- **Workhorse model role:** Runtime: applies conversion rules to transient document content and self-scores against the rubric
- **Cursor workflow:** Agent builds document in/out pipeline, style-rule engine, side-by-side review UI, rubric regression tests
- **Stack:** Next.js, stateless processing functions, docx handling, Stripe
- **Build days:** 12
- **Setup AUD:** $500 (accessibility consultant review of rules)
- **Pricing AUD:** $49–99/month
- **Conservative Y1 midpoint revenue AUD:** $7,500
- **Validation probability:** ~35% (estimate)
- **First-customer route:** Existing NDIS-provider clients; disability-sector communications teams
- **Risk:** Quality bar set by accessibility professionals — partner, don't bypass; niche budgets

### Rank 50 — LocalTongue Sites
- **Category:** AI Localisation
- **Target:** Trades and services in multicultural areas (Western Sydney, SE Melbourne)
- **Problem:** Businesses lose customers who search and browse in Vietnamese, Mandarin, Arabic, Punjabi; agency translation is unaffordable
- **Solution:** Maintains translated versions of key site pages with correct hreflang setup and human-in-the-loop review by community reviewers the business nominates
- **Architect model role:** Design-time: designs glossary/tone controls per language and review workflow
- **Workhorse model role:** Runtime: draft translation constrained by glossary; flags low-confidence segments for the nominated reviewer
- **Cursor workflow:** Agent builds CMS sync, translation-memory store, hreflang generator, review queue with tests
- **Stack:** Next.js, Supabase, WordPress API, hosted LLM API, Stripe
- **Build days:** 14
- **Setup AUD:** $300
- **Pricing AUD:** $59–129/month by languages/pages
- **Conservative Y1 midpoint revenue AUD:** $6,500
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Clients in multicultural trade areas; migrant business associations
- **Risk:** Machine-translation quality perception; reviewer availability per language

### Rank 52 — PolyIVR
- **Category:** AI Localisation
- **Target:** Service businesses in multicultural areas fielding non-English calls
- **Problem:** Language mismatch on first contact loses the job immediately
- **Solution:** Phone front-end that detects caller language, captures job details in-language via guided voice flow, and delivers an English lead summary; recordings purged after processing
- **Architect model role:** Design-time: designs per-language capture flows and translation-summary format
- **Workhorse model role:** Runtime: in-language dialogue within the flow and cross-language summarisation
- **Cursor workflow:** Agent builds telephony flow config as code, per-language test scripts, summary pipeline
- **Stack:** Telephony-AI platform (verify vendor terms), Twilio, serverless functions, Stripe
- **Build days:** 20
- **Setup AUD:** $600
- **Pricing AUD:** $99–199/month + usage
- **Conservative Y1 midpoint revenue AUD:** $6,000
- **Validation probability:** ~25% (estimate)
- **First-customer route:** Same multicultural-area clients as LocalTongue; bundle
- **Risk:** Voice quality across languages varies; higher build complexity

### Rank 54 — QuoteLingo
- **Category:** AI Localisation
- **Target:** Tradies and services quoting to non-English-speaking customers
- **Problem:** Quotes and service terms get misunderstood, causing disputes and lost acceptances
- **Solution:** Generates bilingual quote/invoice PDFs (English + customer's language side-by-side) from existing quote data, with a fixed reviewed glossary for trade terms
- **Architect model role:** Design-time: builds per-trade bilingual glossaries with native-speaker review; designs side-by-side templates
- **Workhorse model role:** Runtime: glossary-constrained translation of quote line items and terms
- **Cursor workflow:** Agent builds quote-import (CSV/ServiceM8), bilingual PDF renderer, glossary tests
- **Stack:** Next.js, PDF generation, Supabase, Stripe
- **Build days:** 8
- **Setup AUD:** $400 (glossary review by native speakers)
- **Pricing AUD:** $19–39/month
- **Conservative Y1 midpoint revenue AUD:** $4,000
- **Validation probability:** ~25% (estimate)
- **First-customer route:** Tradie clients working in multicultural suburbs
- **Risk:** Narrow use case; best as an add-on to QuickQuote Builder rather than standalone

---

## Category 14: AI Personalisation

### Rank 51 — ProposalTailor
- **Category:** AI Personalisation
- **Target:** B2B service SMBs sending templated proposals
- **Problem:** Identical proposals read as identical; win rates suffer against tailored competitors
- **Solution:** Rewrites proposal sections to reference the prospect's public context (industry, stated goals, website language) and past interactions the user supplies — grounded personalisation, not invention
- **Architect model role:** Design-time: designs grounding rules (only user-supplied or public facts), tone profiles, and a "no fabrication" test suite
- **Workhorse model role:** Runtime: constrained rewriting of proposal sections with citations to the grounding facts used
- **Cursor workflow:** Agent builds DOCX in/out pipeline, grounding-fact store, fabrication red-team tests
- **Stack:** Next.js, docx handling, Supabase, Stripe
- **Build days:** 10
- **Setup AUD:** $200
- **Pricing AUD:** $39–79/month
- **Conservative Y1 midpoint revenue AUD:** $6,000
- **Validation probability:** ~30% (estimate)
- **First-customer route:** MSP/agency peers; dogfood on the firm's own proposals
- **Risk:** Generic-AI-writing overlap; grounding discipline is the differentiator

### Rank 53 — SuburbSwap Pages
- **Category:** AI Personalisation
- **Target:** Local service businesses running Google Ads to a single generic landing page
- **Problem:** Ad clicks from different suburbs/services hit one generic page; conversion suffers
- **Solution:** Dynamically personalises landing-page headline, testimonials and job examples by ad keyword/suburb using pre-generated, human-approved variants (no live generation on user traffic)
- **Architect model role:** Design-time: designs variant matrix and pre-generation quality gates
- **Workhorse model role:** Build-time batch: generates the variant pool for human approval; runtime is deterministic swapping only
- **Cursor workflow:** Agent builds variant generator, approval UI, edge-function swapper, conversion tracking with tests
- **Stack:** Edge functions, Next.js, Supabase, Stripe
- **Build days:** 12
- **Setup AUD:** $250
- **Pricing AUD:** $49–99/month
- **Conservative Y1 midpoint revenue AUD:** $5,500
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Clients whose Google Ads the firm already sees underperforming
- **Risk:** Requires clients actually running paid traffic; measurement discipline needed to prove lift

### Rank 55 — ListRevive
- **Category:** AI Personalisation
- **Target:** SMBs sitting on dormant customer lists (salons, mechanics, training providers)
- **Problem:** Past customers are the cheapest revenue, but re-engagement campaigns never get written
- **Solution:** Segments the dormant list by recency/service history (names and service dates only) and drafts personalised win-back sequences for approval and export to their sending tool
- **Architect model role:** Design-time: designs segmentation heuristics and offer-angle library per industry
- **Workhorse model role:** Runtime: drafts per-segment message variants within brand-tone constraints
- **Cursor workflow:** Agent builds CSV import with field-minimisation, segmenter, campaign drafting UI, export adapters
- **Stack:** Next.js, Supabase, Stripe
- **Build days:** 8
- **Setup AUD:** $150
- **Pricing AUD:** $29–59/month or per-campaign
- **Conservative Y1 midpoint revenue AUD:** $4,500
- **Validation probability:** ~30% (estimate)
- **First-customer route:** Any existing client with a customer list; instant demo value
- **Risk:** Spam-compliance (consent status of old lists) must be surfaced to the user; one-off usage pattern hurts retention

### Rank 56 — NewsShaper
- **Category:** AI Personalisation
- **Target:** SMBs sending one generic newsletter to everyone
- **Problem:** One-size-fits-all newsletters get 15% opens and no action
- **Solution:** Splits each newsletter into interest-based variants (drawn from click/segment history in their email platform) with per-segment subject lines and intros, pushed back to their platform for sending
- **Architect model role:** Design-time: designs segment-inference approach from engagement metadata and variant style guide
- **Workhorse model role:** Runtime: drafts per-segment variants of the user's base newsletter
- **Cursor workflow:** Agent builds email-platform API integrations (Mailchimp-class), variant editor, send-back flow with tests
- **Stack:** Next.js, email platform APIs, Supabase, Stripe
- **Build days:** 12
- **Setup AUD:** $200
- **Pricing AUD:** $29–59/month
- **Conservative Y1 midpoint revenue AUD:** $4,000
- **Validation probability:** ~25% (estimate)
- **First-customer route:** Clients already sending newsletters through platforms the firm set up
- **Risk:** Email platforms shipping native AI personalisation; small budget line

---

## Top 10 Picks — One-Line Build Plans

1. **MissedCall Rescue** (Receptionist, rank 1) — Wire a Twilio missed-call webhook to an SMS qualification state machine with per-trade scripts, ship the lead-card dashboard, and install it on three existing tradie clients' numbers in week two.
2. **SWMS Studio** (Tradie/NDIS, rank 2) — Build the hazard/control library and guided form first, pay a WHS consultant to review the per-trade templates, then ship DOCX/PDF export and sell through existing builder clients to their subbies.
3. **InvoiceChase Copilot** (AI Workflow, rank 3) — Start Xero app approval immediately, build the escalation-sequence engine against sandbox data in parallel, and pilot on two clients' real aged-receivables with approval-gated sends.
4. **Inbox2Job** (AI Workflow, rank 4) — Build the mail-in extraction pipeline with Zod-validated job-card schema and a ServiceM8 push adapter, then install for existing ServiceM8 clients during routine IT visits.
5. **AuditReady** (Tradie/NDIS, rank 5) — Encode the public practice-standards indicators into a checklist/evidence data model, validate with one NDIS consultant, and pilot with an existing provider client ahead of their next audit.
6. **SubbieCheck** (Service Platforms, rank 6) — Build subbie self-upload portal plus certificate parsing with human confirmation, seed with one builder client's real subbie list, and let expiry alerts prove value in month one.
7. **SnapReport** (AI Workflow, rank 7) — Ship the PWA photo/voice capture and one electrician report template end-to-end, generate a real client's next job report side-by-side with their manual one, then add templates per trade.
8. **AreaPages** (AI Content+SEO, rank 8) — Build the suburb-data grounding pipeline and WordPress publisher, launch on two client sites the firm already manages, and use ranking movement as the case study.
9. **ReviewReply Desk** (AI Tools SMB, rank 9) — Integrate the Google Business Profile API with a tone-profiled reply drafter and approval queue, onboard three local clients from the existing book, and bundle GBP Autopilot as the upsell.
10. **AfterHours Voice Agent** (AI Receptionist, rank 10) — Configure a telephony-AI platform flow as versioned code with a simulated-call test harness, pilot after-hours only for one plumber currently paying a human answering service, and expand on proven call quality.

**Portfolio note:** ranks 1–7 share a customer (the existing tradie/NDIS client base), a stack (Next.js/Supabase/Twilio/Stripe + provider-agnostic LLM layer), and cross-sell paths (MissedCall → VoicemailTriage → Inbox2Job → SnapReport; SWMS → ToolboxTalk → SubbieCheck → CertVault). Build rank 1 first, reuse its billing/onboarding/SMS plumbing for everything after.

---

## Four-Tier Routing Pattern

Use task shape, not prestige, to select a model. The example names below are documented by Cursor as of July 2026, but availability varies by account and can change.

| Tier | Use it for | Current examples | Guardrail |
|---|---|---|---|
| Frontier architect | Architecture, threat modelling, difficult migrations, eval design | Claude Fable 5, Claude Opus 4.8, GPT-5.6 Sol | Use for the few decisions where deeper reasoning changes the design |
| Balanced implementation | Multi-file features, complex debugging, code review | The best currently available balanced coding model | Require focused tests; do not use model reputation as evidence |
| Fast workhorse | Bounded edits, extraction, fixtures, formatting, repetitive tests | Auto, Composer 2.5, or another currently available fast model | Keep prompts narrow and outputs schema-constrained |
| Built-in workflow | Routine routing and genuinely large-context work | Auto; Max Mode when larger context materially helps | Auto's underlying model is not disclosed; Max Mode is context, not guaranteed intelligence |

For this opportunity portfolio: use one frontier pass to define the product boundary, data model, abuse cases, and evaluation set; use balanced/workhorse models for implementation; use deterministic code and human approval for money, safety, compliance, and external publishing.

## Token-Saving Cheat Sheet

- Give Agent only the relevant files, acceptance criteria, and failing evidence; avoid repeatedly attaching the whole repository.
- Use Inline Edit for self-contained changes and include all required local context in that prompt. It is a separate workflow, but no blanket “zero context cost” claim is made.
- Reuse stable project instructions in `.cursor/rules/*.mdc`; keep task-specific detail in the task prompt.
- Prefer schemas, fixtures, and compact structured payloads over prose-heavy runtime prompts.
- Cache safe, repeatable results; hash large payloads in logs; cap output by task.
- Use Auto for routine work and Max Mode only when the larger context window is necessary.

## Continuous Testing Loop

1. **Plan:** define one measurable initial success criterion, product boundary, data-minimisation rule, and failure modes.
2. **Build:** implement the smallest end-to-end slice with provider adapters and deterministic business rules.
3. **Test:** run unit/integration tests, a real workflow smoke test, and adversarial cases for prompt injection, hallucinated facts, and unsafe automation.
4. **Verify:** compare evidence with the success criterion; require human approval for outbound messages, prices, safety/compliance drafts, and publishing.
5. **Iterate:** fix the highest-signal failure and repeat, with a maximum of five cycles before narrowing or stopping the bet.
6. **Finalise:** record conversion, retention, support burden, model cost, and the decision to scale, revise, or stop.

## Project Rule

The executable project guidance is in `.cursor/rules/model-routing.mdc`. The linked page's suggested root `.cursorrules` format is outdated; current Cursor documentation recommends `.cursor/rules/*.mdc` or `AGENTS.md`.

## Cursor Pro Power-User Tips

1. Use Auto for routine work; explicitly select a frontier model only when the decision is architecture- or risk-sensitive.
2. Keep model identifiers configurable and discover API identifiers at runtime. IDE display names are not a stable API contract.
3. Turn on Max Mode only for work that truly needs a larger context window.
4. Put repeatable repository constraints in project rules, but remember those rules do not apply to Cursor Tab or Inline Edit.
5. Treat Bugbot and model reviews as advisory; reproduce findings and verify fixes with tests.

## AU Validation Guardrails

- The [OAIC's commercial AI guidance](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products) says privacy obligations can apply to both personal information entered into an AI system and personal information in its outputs. Conduct due diligence, minimise data, define retention, and embed human oversight.
- The [NDIS Commission](https://www.ndiscommission.gov.au/rules-and-standards/reportable-incidents-and-incident-management/incident-management) requires registered providers to maintain incident-management systems and protect the privacy and confidentiality of records. Products handling participant content need a separate privacy/security assessment; “transient processing” alone does not remove the risk.
- The [ACCC](https://www.accc.gov.au/consumers/advertising-and-promotions/false-or-misleading-claims) requires business claims to be truthful, accurate, and based on reasonable grounds. AI-generated marketing, review replies, and local pages need human approval and evidence for factual claims.

*All revenue figures, probabilities and rankings in this document are planning estimates, not market research or guarantees. Validate the top idea with five problem interviews and three paid pilots before building the broader portfolio. Verify current AI-provider terms, platform API requirements, and SMS/telephony obligations before committing to a build.*
