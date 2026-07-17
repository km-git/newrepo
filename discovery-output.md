# Australian Micro-SaaS Discovery Portfolio

Generated 17 July 2026 from the linked brief. The rankings favour forced demand, accessible distribution, narrow MVP scope, low PII exposure, and recurring use.

> **Estimate warning:** Build time, cost, price, revenue, and success percentages are planning estimates, not forecasts. “Success” means reaching roughly A$2,000 MRR within 12 months. Validate the problem with 10 buyer interviews and a paid pilot before building. Products that draft compliance material must remain decision-support tools, require customer review, and receive appropriate professional review before launch.

## 1. Ranked portfolio (56 ideas)

| # | Name | Category | Target | Problem | Solution | Architect Model | Workhorse Models | Cursor Workflow | Stack | Build Days | Setup A$ | Pricing | Y1 Mid Rev A$ | Success % | First Customer | Risk |
|---:|---|---|---|---|---|---|---|---|---|---:|---:|---|---:|---:|---|---|
| 1 | ScreenTrack | Tradie/NDIS | NDIS providers with 2–30 workers | Screening and credential registers expire unnoticed | Expiry register, 90/60/30-day alerts, audit export | Claude Opus 4.8 | Auto + Composer 2.5 | Encode rules; build CRUD; test alert timing | Next.js, Supabase AU, Resend | 10 | 200 | A$25–99/mo | 30,000 | 40% | NDIS auditor referral | Rostering suites bundle it |
| 2 | RefundRight | AI Compliance | AU Shopify/WooCommerce stores | Refund pages contain ACL-risk wording | Crawl policies, cite flagged phrases, draft replacements | GPT-5.6 Sol | Auto + Composer 2.5 | Build rules corpus; crawl; accuracy eval | Next.js, Playwright, Shopify app | 12 | 400 | Free scan + A$19/mo | 18,000 | 45% | Shopify App Store | Must not imply legal advice |
| 3 | TextBack | AI Tools SMB | Service SMBs missing calls | Callers abandon voicemail and book competitors | Missed call triggers AI SMS intake and lead card | GPT-5.6 Sol | Auto + Sonnet 5 | Model state machine; simulate conversations; pilot number | Next.js, Twilio, Supabase | 7 | 150 | A$49/mo | 18,000 | 35% | Live demo to local tradies | Call-forwarding setup friction |
| 4 | FreshABN | Lead Gen | Accountants, agencies, brokers | Weekly ABN entries are raw XML | Filtered new-business lead feeds and CRM webhooks | Claude Fable 5 | Auto + Composer 2.5 | Parse extracts; diff fixtures; verify dedupe | Python, Postgres, Next.js | 12 | 150 | A$49–149/mo | 18,000 | 35% | Suburban accounting firm | Commoditised public data |
| 5 | SiteSafe SWMS | Micro-SaaS Vertical | Small high-risk construction crews | Site-specific SWMS creation is slow | Guided job-specific draft, sign-on, versioned PDF | Claude Opus 4.8 | Auto + Sonnet 5 | Encode checklist; golden-file tests; mobile smoke | Next.js PWA, Supabase, PDF | 18 | 900 | A$19–49/mo | 30,000 | 35% | Trade-association pilot | Safety/liability expectations |
| 6 | TenderScout AU | Vertical AI Agents | Government-supplier SMEs | Relevant tenders are hard to find and assess | Monitor portals, score fit, draft response skeleton | Claude Fable 5 | Auto + Sonnet 5 | Ingest feeds; build eval set; nightly scoring | Next.js, Postgres, workers, LLM | 20 | 300 | A$99–199/mo | 45,000 | 35% | Civil contractor via LinkedIn | Portal and scraper changes |
| 7 | FoodLog 3.2.2A | Micro-SaaS Vertical | Cafés, caterers, food vans | Daily food-safety records are missed or lost | Mobile logs, range flags, corrective notes, export | GPT-5.6 Sol | Auto + Composer 2.5 | Map required records; offline build; venue walkthrough | Next.js PWA, Supabase | 12 | 200 | A$25–39/mo | 24,000 | 30% | Independent café pilot | Paper remains “good enough” |
| 8 | PixelPatrol AU | AI Compliance | AU sites using ad pixels | Pixel use and policy disclosures drift | Quarterly network scan and OAIC-aligned report | Claude Fable 5 | Auto + Composer 2.5 | Build signature DB; benchmark detections; report | Playwright, Next.js, object storage | 18 | 400 | A$49/site/mo | 20,000 | 40% | Privacy consultant reseller | Global scanners localise |
| 9 | QuizKit AU | AI Personalisation | AU Shopify brands on Klaviyo | Generic journeys convert poorly; tracking adds risk | Catalog-generated zero-party quiz and consent sync | Claude Fable 5 | Auto + Composer 2.5 | Generate quiz; visual test widget; sandbox sync | Shopify Remix, Preact, Klaviyo | 25 | 500 | A$29–99/mo | 22,000 | 35% | Skincare brand case study | Mature global incumbents |
| 10 | TradieIntake AI | AI Workflow | ServiceM8 trade businesses | Calls and forms require manual job entry | Convert enquiries into idempotent job cards | Claude Opus 4.8 | Auto + Sonnet 5 | Design retries; sandbox E2E; duplicate tests | TypeScript, Twilio, ServiceM8 | 18 | 300 | A$39–79/mo | 20,000 | 35% | ServiceM8 add-on listing | Platform adds native feature |
| 11 | ABNPulse | Dev Tools | AU SaaS and commerce developers | Official ABR service is awkward to integrate | REST API, SDKs, bulk validation, status webhooks | Claude Fable 5 | Auto + Composer 2.5 | Specify API; ingest extract; contract tests | Fastify, Postgres, Railway | 12 | 150 | Free + A$29–99/mo | 12,000 | 30% | Developer SEO | Free official service suffices |
| 12 | PriceWatch NDIS | Vertical AI Agents | Small NDIS providers | Price-guide changes are hard to map to services | Diff catalogues and send item-specific alerts | Claude Opus 4.8 | Auto + Sonnet 5 | Historical diff fixtures; parser tests; digest | Next.js, Supabase, PDF/CSV workers | 15 | 200 | A$19–49/mo | 30,000 | 35% | Provider Facebook group | NDIA improves notifications |
| 13 | GapFill | Service Platforms | Small Cliniko clinics | Cancelled appointments remain empty | Offer slots to waitlist by SMS and auto-book winner | GPT-5.6 Sol | Auto + Composer 2.5 | Sandbox API; race-condition tests; clinic pilot | Next.js, Cliniko, Twilio | 14 | 300 | A$99/clinic/mo | 25,000 | 30% | Allied-health owner group | Cliniko adds native backfill |
| 14 | Aussify | AI Localisation | Cross-border and AU Shopify stores | US language, units and seasons reduce trust | Batch en-AU rewrite with deterministic checks and rollback | GPT-5.6 Sol | Auto + Composer 2.5 | Build rule layer; 500-product snapshot tests | Shopify Remix, LLM API | 12 | 300 | A$15–49/mo | 15,000 | 40% | Cross-border Shopify agency | One-off use causes churn |
| 15 | GSTBoard | Analytics | AU Shopify merchants/bookkeepers | BAS-oriented sales views need manual cleanup | GST-status, fee, refund and account-code reports | Claude Opus 4.8 | Auto + Composer 2.5 | Test-store fixtures; rounding tests; app review | Shopify Remix, Postgres | 18 | 150 | A$19–49/mo | 18,000 | 35% | Shopify App Store | Tax-reporting trust bar |
| 16 | ReviewMate AU | AI Tools SMB | Local service businesses | Reviews go unanswered | Draft on-brand replies with one-tap approval | GPT-5.6 Sol | Auto + Composer 2.5 | API spike; tone evals; approval-flow test | Next.js, GBP API, Supabase | 12 | 200 | A$29–59/location/mo | 25,000 | 30% | Agency reseller | GBP API approval |
| 17 | UnsubGuard | AI Compliance | AU email/SMS agencies | Broken unsubscribe flows create Spam Act exposure | Pre-send linter and synthetic unsubscribe tests | Claude Fable 5 | Auto + Composer 2.5 | Integrate ESPs; scheduled browser E2E tests | Fastify, Playwright, Supabase | 20 | 500 | A$39–129/mo | 22,000 | 35% | CRM agency white-label | ESPs ship checks |
| 18 | AnswerRank AU | AI Content+SEO | AU brands and SEO agencies | AI-answer visibility is opaque | Repeatable prompt tracking, citations and competitor share | Claude Fable 5 | Auto + Sonnet 5 | Multi-engine runner; variance scoring; weekly report | Next.js, Supabase, LLM APIs | 18 | 300 | A$79–199/mo | 38,000 | 30% | Free AI visibility audit | Noisy measurements |
| 19 | QuoteVoice | AI Tools SMB | Tradies without office staff | Quotes are written after hours | Voice/photos to itemised GST-aware quote from rate card | Claude Fable 5 | Auto + Sonnet 5 | Extraction schema; transcript evals; PDF E2E | Next.js PWA, STT, PDF, Stripe | 14 | 200 | A$29–49/mo | 22,000 | 30% | Tradie video demo | Job apps bundle quoting |
| 20 | TenderDraft AI | AI Workflow | SMEs bidding for public work | First-draft tender work is expensive | RAG over capability statements and past responses | Claude Fable 5 | Auto + Sonnet 5 | Retrieval eval; grounded drafting tests; pilot bid | FastAPI, pgvector, Next.js | 25 | 500 | A$99–299/mo | 25,000 | 30% | Tender consultant partner | Output quality expectations |
| 21 | BuildLeads | Lead Gen | Trades selling into renovations | DA buying signals are scattered | Trade-mapped, radius-filtered DA alerts | Claude Opus 4.8 | Auto + Composer 2.5 | Backfill DAs; tune mappings; lead-quality sample | Python, PostGIS, Twilio | 12 | 500 | A$49–99/mo | 15,000 | 30% | Pool builder pilot | DA is not purchase intent |
| 22 | SuburbRank | Analytics | Local SEO agencies | Geo-grid tools are USD-priced and generic | AU suburb rank grids and white-label reports | Claude Opus 4.8 | Auto + Composer 2.5 | Cost guardrails; scheduled scans; report snapshots | Node, SERP API, Postgres | 12 | 300 | A$29–99/mo | 14,000 | 30% | AU SEO agency | SERP data margin |
| 23 | InvoiceRight | Tradie/NDIS | Independent support workers | Wrong support codes and caps delay invoices | Guided invoice builder with catalogue validation | GPT-5.6 Sol | Auto + Composer 2.5 | Ingest catalogue; validation fixtures; PDF walkthrough | Next.js, Supabase AU, PDF | 14 | 150 | A$15–19/mo | 22,000 | 35% | Plan-manager referral | Sensitive identifiers and churn |
| 24 | TradieLine | AI Receptionist | Emergency plumbers/electricians | After-hours calls go to competitors | Disclosed AI answering, triage, booking and transfer | Claude Fable 5 | Auto + Sonnet 5 | State-machine design; scripted call simulations | Twilio, realtime voice, Supabase | 21 | 500 | A$149–299/mo + usage | 40,000 | 30% | Local plumber pilot | Emergency mis-triage |
| 25 | ADMDisclose | AI Compliance | APP entities using automated decisions | New ADM disclosure work is complex | Business-process inventory and draft disclosure register | Claude Opus 4.8 | Auto + Sonnet 5 | Encode rubric; wizard tests; professional review | Next.js, Supabase AU, DOCX | 18 | 900 | A$149 + A$29/mo | 25,000 | 40% | MSP/privacy partner | Deadline-driven demand fades |
| 26 | CALDlocal | AI Localisation | Services in multilingual suburbs | Local language demand is not reflected online | Use census data to generate top-language assets | Claude Fable 5 | Auto + Sonnet 5 | Census pipeline; native-speaker QA rubric; export | Next.js, ABS data, LLM | 18 | 500 | A$149 pack or A$29/mo | 18,000 | 35% | Local SEO agency | Translation quality |
| 27 | CatalogRecs | AI Personalisation | Small AU online stores | Native recommendations are weak; tracking is intrusive | Catalog-only similarity and complementary widgets | Claude Fable 5 | Auto + Composer 2.5 | Embedding eval; widget test; cache benchmark | Shopify app, pgvector, edge cache | 18 | 350 | A$19–59/mo | 16,000 | 35% | Shopify agency | Native recommendations improve |
| 28 | SuburbPage | AI Content+SEO | Trades targeting nearby suburbs | Thin sites cannot cover local intent | Real-job-data-based service/suburb pages | GPT-5.6 Sol | Auto + Sonnet 5 | Uniqueness checks; schema validation; pilot rankings | Next.js, WordPress API, LLM | 14 | 200 | A$59–129/mo | 30,000 | 30% | Two free tradie pilots | Scaled-content penalties |
| 29 | ChaseFlow | AI Tools SMB | Xero B2B small businesses | Overdue invoices need manual follow-up | Tone-controlled email/SMS escalation and analytics | Claude Opus 4.8 | Auto + Composer 2.5 | OAuth sandbox; scheduler E2E; idempotency tests | Next.js, Xero, Twilio | 18 | 300 | A$25–69/mo | 28,000 | 25% | Bookkeeper partner | Xero native reminders |
| 30 | PriceBook Sync | Tradie/NDIS | Material-heavy trade businesses | Supplier price files go stale | Extract invoice prices, show diffs, export to job app | GPT-5.6 Sol | Auto + Sonnet 5 | Real invoice fixtures; extraction accuracy gate | Next.js, Supabase, ServiceM8 | 21 | 400 | A$39/mo | 14,000 | 25% | ServiceM8 user group | Fragile supplier formats |
| 31 | SprayBook | Micro-SaaS Vertical | Farmers and spray contractors | Application records are compulsory and paper-heavy | Offline voice records, weather fill, compliant export | Claude Fable 5 | Auto + Composer 2.5 | Required-field schema; offline sync tests; field pilot | Expo/PWA, Supabase, BOM API | 20 | 300 | A$15–35/mo | 18,000 | 25% | Agronomist referral | Rural distribution |
| 32 | DocHound | Vertical AI Agents | Bookkeeping practices | BAS document chasing consumes deadline weeks | Escalating chase agent and missing-item board | GPT-5.6 Sol | Auto + Composer 2.5 | Cadence engine; reply-parsing simulations | Next.js, email API, Twilio | 16 | 300 | A$49–99/mo | 32,000 | 30% | Bookkeeper association | Practice suites bundle it |
| 33 | ClinicVoice | AI Receptionist | Small Cliniko clinics | Calls interrupt treatment and go unanswered | Disclosed voice agent books and answers non-clinical FAQs | Claude Fable 5 | Auto + Sonnet 5 | Privacy guardrails; Cliniko sandbox; call evals | Twilio, realtime voice, Cliniko | 25 | 500 | A$199/mo + usage | 30,000 | 27% | Physio owner community | Health-adjacent privacy |
| 34 | AddrKit AU | Dev Tools | AU form and checkout developers | G-NAF is authoritative but cumbersome | Hosted AU address typeahead and validation API | Claude Opus 4.8 | Auto + Composer 2.5 | Loader; relevance eval; quarterly refresh job | Go, Typesense, PostGIS | 18 | 500 | A$19–149/mo | 15,000 | 25% | Shopify developer | Established vendors |
| 35 | NoShow Shield | Service Platforms | Independent salons/barbers | No-shows hit revenue; booking suites feel heavy | Deposit link, reminders, reschedule and waitlist | Claude Opus 4.8 | Auto + Composer 2.5 | Booking E2E; payment webhooks; mobile test | Next.js, Stripe, Twilio | 14 | 250 | A$59/mo | 20,000 | 30% | Solo stylist via Instagram | Free booking platforms |
| 36 | FeedLocal AU | AI Localisation | AU Shopping and Meta advertisers | Feeds carry US sizes, units and tax display | Deterministic AU feed transformations with AI fallback | GPT-5.6 Sol | Auto + Composer 2.5 | Golden feeds; transform tests; scheduled export | Node, Content API, Postgres | 18 | 350 | A$39–149/mo | 16,000 | 35% | Performance agency | Generic feed tools |
| 37 | ProfilePulse | AI Content+SEO | Local SMBs and agencies | Business profiles go stale | AU-seasonal post kits, Q&A prompts and approval | GPT-5.6 Sol | Auto + Composer 2.5 | Calendar generator; publish integration; cron tests | Next.js, GBP API, Supabase | 14 | 200 | A$19–39/location/mo | 26,000 | 25% | Small marketing agency | GBP API and feature changes |
| 38 | TenderRadar | Lead Gen | SMEs below enterprise aggregator budgets | Tender portals are fragmented | Cross-portal alerts with capability fit reasons | Claude Fable 5 | Auto + Composer 2.5 | One connector per portal; resilience tests | Python, Postgres, email | 25 | 400 | A$39–129/mo | 14,000 | 25% | TenderDraft funnel | Scraper maintenance |
| 39 | GeoBlocks | AI Personalisation | Privacy-conscious AU sites | Generic pages underperform; tracking adds burden | State, season, device and referrer content blocks | GPT-5.6 Sol | Auto + Composer 2.5 | Edge rules; aggregate A/B tests; embed demo | Cloudflare Workers, KV, JS embed | 15 | 300 | A$25–79/mo | 14,000 | 30% | CRO agency | Uplift may be too small |
| 40 | ParcelScope | Analytics | AusPost contract merchants | Tracking events lack lane-level performance views | Transit percentiles, exceptions and promise accuracy | GPT-5.6 Sol | Auto + Composer 2.5 | Event replay; state-machine tests; merchant pilot | Node, Timescale, Next.js | 18 | 150 | A$49–149/mo | 12,000 | 25% | E-commerce operator group | Shipping suites overlap |
| 41 | StrataMinute | Micro-SaaS Vertical | Self-managed strata schemes | Meeting notices, minutes and retention are error-prone | Agenda templates, transcript draft, archive and reminders | Claude Opus 4.8 | Auto + Sonnet 5 | NSW-first rules; transcript eval; state expansion | Next.js, STT, Supabase | 16 | 300 | A$149/year | 20,000 | 25% | Self-managed strata group | State-law differences |
| 42 | OpenHome Agent | Vertical AI Agents | Independent real-estate offices | Listing enquiries arrive after hours | Listing-grounded answers and inspection booking | Claude Fable 5 | Auto + Sonnet 5 | Strict RAG; adversarial claims eval; escalation | Next.js, Supabase, SMS/email | 20 | 400 | A$149–299/office/mo | 40,000 | 25% | Lighthouse agency | Misleading property claims |
| 43 | PlanPace | Tradie/NDIS | Support coordinators | Budgets and plan duration live in spreadsheets | Burn-rate alerts, review countdowns and reports | Claude Fable 5 | Auto + Sonnet 5 | Data model; pacing-math tests; privacy review | Next.js, Supabase AU, charts | 21 | 300 | A$79/org/mo | 18,000 | 27% | Coordinator community | Data-entry burden and PII |
| 44 | PM AfterHours | AI Receptionist | Property-management offices | Urgent tenant calls hit personal mobiles | Disclosed voice triage against agency escalation matrix | Claude Fable 5 | Auto + Sonnet 5 | Over-escalation rules; simulated tenant calls | Twilio, realtime voice, Supabase | 21 | 500 | A$249/office/mo | 28,000 | 27% | Independent PM office | Emergency classification |
| 45 | QuoteTriage | Service Platforms | Small self-managed strata | Requests and contractor quotes scatter across email | Resident intake, three-quote compare and approval log | Claude Fable 5 | Auto + Composer 2.5 | Permission schema; audit tests; committee walkthrough | Next.js, Supabase, Resend | 21 | 300 | A$49/building/mo | 12,000 | 20% | Strata committee | Slow committee sales |
| 46 | ResidencyLint | Dev Tools | AU agencies and B2B SaaS | Data-residency questionnaires are manual | CI scanner for regions, endpoints and SDK configs | Claude Fable 5 | Auto + Composer 2.5 | Rule taxonomy; fixture repos; CI report | Rust/TypeScript CLI, GitHub Action | 17 | 100 | Free + A$49–199/mo | 10,000 | 20% | Security consultancy | One-off audit behaviour |
| 47 | GSTShow | AI Localisation | Overseas sellers entering AU | Consumer prices may exclude GST or hide total | Crawl price display and supply compliant storefront widget | GPT-5.6 Sol | Auto + Composer 2.5 | DOM heuristics; theme visual tests; audit report | Playwright, JS embed, Next.js | 12 | 300 | A$29/mo | 12,000 | 30% | Cross-border agency | Platforms already support setup |
| 48 | ListingPen AU | AI Content+SEO | Real-estate agents | Every listing needs channel variants and claim checks | AU copy variants plus unverifiable-claim linter | Claude Opus 4.8 | Auto + Sonnet 5 | Claims corpus; listing eval set; export tests | Next.js, multimodal LLM | 10 | 150 | A$29/agent/mo | 22,000 | 20% | Agent coach affiliate | Thin moat versus ChatGPT |
| 49 | DAScope AI | AI Workflow | Builders, suppliers and planners | DA feeds are noisy | Classified plain-English suburb/category digests | GPT-5.6 Sol | Auto + Composer 2.5 | Historical backfill; classification eval; digest | Python, Postgres, Resend | 12 | 500 | A$29–99/mo | 12,000 | 25% | Pool supplier | Upstream API coverage |
| 50 | ReviewPing | Service Platforms | Trades and clinics | Happy customers rarely leave reviews unprompted | Job-complete SMS request and velocity report | Claude Opus 4.8 | Auto + Composer 2.5 | Webhook adapters; consent copy; SMS E2E | Next.js, Twilio, ServiceM8 | 10 | 200 | A$49/mo | 18,000 | 25% | ServiceM8 add-on | Crowded category |
| 51 | VetDesk | AI Receptionist | Independent veterinary clinics | Routine calls overwhelm reception | Booking, message capture and hard-coded emergency routing | Claude Fable 5 | Auto + Sonnet 5 | Vet intents; emergency regression calls; pilot | Twilio, realtime voice, Supabase | 21 | 500 | A$199–299/mo | 25,000 | 25% | Vet practice-manager group | Emergency risk and API access |
| 52 | StackSpy AU | Lead Gen | Web agencies | Outdated-stack prospects are hard to identify | Evidence-backed AU website technology lead lists | Claude Opus 4.8 | Auto + Composer 2.5 | Crawl etiquette; fingerprint fixtures; sampling | Go crawler, ClickHouse, Next.js | 25 | 800 | A$79–199/mo | 12,000 | 20% | AU digital agency | Discovery coverage and TOS |
| 53 | SegmentSwap | AI Personalisation | Multi-segment product brands | One product page cannot serve distinct buyers | Self-selected persona toggle with generated variants | GPT-5.6 Sol | Auto + Composer 2.5 | Variant pipeline; aggregate A/B test; embed | JS component, Next.js, LLM | 12 | 250 | A$29–79/mo | 12,000 | 30% | Landing-page agency | Unproven interaction pattern |
| 54 | SpotWatch | Analytics | Spot-exposed energy users | AEMO feeds are hard to interpret | Five-minute price alerts and interval-file analytics | Claude Fable 5 | Auto + Composer 2.5 | Feed poller; historical threshold backtest | Python, Timescale, Next.js | 18 | 200 | A$15–59/mo | 8,000 | 20% | Energy consultant | Narrow paying niche |
| 55 | OzPing | Dev Tools | AU SaaS and agencies | Global probes miss AU-specific failures | Sydney/Melbourne/Brisbane/Perth probes and status pages | GPT-5.6 Sol | Auto + Composer 2.5 | Soak test scheduler; alert dedupe; failover | Go, Postgres, AU VPS nodes | 18 | 400 | A$15–99/mo | 9,000 | 20% | AU startup community | Incumbents add probes |
| 56 | CampaignDownunder | AI Workflow | Agencies localising global campaigns | US copy, seasons and claims need manual adaptation | AU tone/calendar adaptation plus ACL-risk flags | Claude Opus 4.8 | Auto + Sonnet 5 | Build US→AU eval set; Docs add-on; QA | Next.js, LLM, Google add-on | 10 | 250 | A$49–199/mo | 14,000 | 30% | AU agency copy lead | General LLMs replicate it |

The mean estimated success rate is about 30%, satisfying the brief’s blended threshold; it does **not** imply that 30% of launches will succeed.

## 2. Top 10 build sequence

1. **ScreenTrack** — Start with 10 providers and two auditors; build the expiry-register core with Claude Opus 4.8, then Auto/Composer 2.5.
2. **RefundRight** — Build a citation-backed deterministic rules corpus before adding GPT-5.6 Sol classification.
3. **TextBack** — Prove the whole experience on one Twilio number before adding integrations.
4. **FreshABN** — Validate weekly extract diffs and sell a CSV subscription before building CRM connectors.
5. **SiteSafe SWMS** — Obtain professional template review, then implement a constrained document workflow.
6. **TenderScout AU** — Hand-score 100 tenders with five SMEs before training the relevance rubric.
7. **FoodLog 3.2.2A** — Run a mobile paper-to-PWA pilot in one café and optimise completion time.
8. **PixelPatrol AU** — Benchmark detection against known pixels, then sell through privacy consultants.
9. **QuizKit AU** — Launch one vertical template and demonstrate conversion lift before broadening.
10. **TradieIntake AI** — Use ServiceM8’s sandbox and make duplicate-job prevention the release gate.

## 3. Four-tier Cursor routing

The linked page’s exact inventory and benchmark claims should not be treated as durable facts. Model availability varies by account and changes frequently; check **Settings → Models** and the official pricing page.

1. **Frontier architecture:** Claude Fable 5, Claude Opus 4.8, or GPT-5.6 Sol for hard schemas, safety boundaries, migrations, and high-risk design.
2. **Daily heavy work:** Claude Sonnet 5 for implementation, review, and medium-complexity debugging.
3. **Routine workhorse:** Auto for everyday work and Composer 2.5 for long agentic coding; both currently draw from Cursor’s first-party usage pool.
4. **Specialised execution:** Cloud Agents for isolated build/test work, Max Mode only when extended context is necessary, and Bugbot for PR review.

Use the cheapest adequate option, but route safety-, privacy-, money-, and compliance-critical decisions to deeper review. A strong model does not replace runtime tests or professional review.

## 4. Token-saving cheat sheet

- Start with a precise success criterion, affected files, constraints, and exact test command.
- Use Auto for routine work; switch models only when complexity justifies it.
- Keep one conversation while its context remains relevant; start fresh when the task changes.
- Attach only the files and logs needed for the current decision.
- Put stable repository guidance in `.cursor/rules/*.mdc`; do not repeat it in every prompt.
- Use Tab for local completions and Composer 2.5 for coherent multi-file work.
- Use Max Mode only for genuinely large-context tasks because it consumes usage faster.

## 5. Continuous validation loop

1. **Plan:** Define one measurable intended-success criterion, data boundaries, and rollback.
2. **Build:** Implement the thinnest end-to-end path.
3. **Test:** Run unit/integration tests plus a real user-flow smoke test.
4. **Verify:** Check the intended-success criterion and inspect privacy, cost, and failure modes.
5. **Iterate:** Repeat up to five cycles; if buyer evidence or reliability remains weak, cut or narrow the bet.
6. **Finalise:** Record outcome, evidence, unit economics, and the next validation milestone.

## 6. Cursor project rule

The linked instruction to create `.cursorrules` is outdated. Current Cursor project rules live in `.cursor/rules/*.mdc`; this repository includes `.cursor/rules/portfolio-build.mdc`.

## 7. High-impact Cursor practices

- Ask for a file-level plan and acceptance criteria before invasive changes.
- Delegate independent research or implementation slices to parallel subagents, then require one integration owner.
- Give Cloud Agents a reproducible environment and exact end-to-end test path.
- Run Bugbot on the branch diff, but treat it as an additional reviewer rather than a test substitute.
- Save a screenshot/video artifact for UI work and terminal output for non-UI end-to-end proof.

## Sources and verification notes

Primary and official sources were preferred for load-bearing claims:

- [ABS — Counts of Australian Businesses](https://www.abs.gov.au/statistics/economy/business-indicators/counts-australian-businesses-including-entries-and-exits/latest-release)
- [ABR — Web Services](https://abr.business.gov.au/Tools/WebServices/1000) and [ABN Bulk Extract](https://www.data.gov.au/data/dataset/abn-bulk-extract)
- [SafeWork NSW — SWMS](https://www.safework.nsw.gov.au/your-industry/construction/construction/general-requirements/prepare-safe-work-method-statement)
- [FSANZ — Food Safety Management Tools](https://www.foodstandards.gov.au/business/food-safety/overview-food-safety-management-tools)
- [NSW EPA — Pesticide record keeping](https://www.epa.nsw.gov.au/Your-environment/Pesticides/compulsory-record-keeping)
- [NDIS Commission — Worker screening](https://www.ndiscommission.gov.au/workforce/worker-screening)
- [NDIS — Pricing arrangements](https://www.ndis.gov.au/providers/pricing-arrangements)
- [Department of Finance — Procurement statistics](https://www.finance.gov.au/government/procurement/statistics-australian-government-procurement-contracts-)
- [PlanningAlerts API](https://www.planningalerts.org.au/api/howto)
- [ServiceM8 Developer](https://developer.servicem8.com/)
- [Xero Small Business Insights](https://www.xero.com/au/resources/small-business-insights/latest-australia/)
- [OAIC — Tracking pixels guidance](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/organisations/tracking-pixels-and-privacy-obligations)
- [ACCC — Online returns policy sweep](https://www.accc.gov.au/media-release/accc-sweep-uncovers-concerning-online-shopping-return-policies-and-terms-and-conditions)
- [ACMA — Spam investigations](https://www.acma.gov.au/investigations-spam-and-telemarketing)
- [ABS — Cultural diversity](https://www.abs.gov.au/statistics/people/people-and-communities/cultural-diversity-census/latest-release)
- [Cursor — Models and pricing](https://cursor.com/docs/models-and-pricing)
- [Cursor — Rules](https://cursor.com/docs/rules)
- [Cursor — Cloud Agents](https://cursor.com/docs/cloud-agent)
- [Cursor — Bugbot](https://cursor.com/docs/bugbot)

Vendor-published missed-call, review, no-show, conversion, and competitor-pricing figures were used only as directional signals and were not promoted to factual guarantees. Before choosing a bet, re-check API access, platform terms, current legislation, and named competitor pricing.
