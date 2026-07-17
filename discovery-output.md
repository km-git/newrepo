# AU Micro-Venture Discovery: 50 AI-Powered Small Bets

A portfolio scan for a 1-2 person Australian IT/AI consultancy shipping fast with Cursor. Every idea fits the constraints: 7-30 day build, A$0-2K setup, A$0-500/mo recurring, A$1-50K/mo revenue ceiling, and compliance framed around the AU Privacy Act (APPs) and Australian Consumer Law. Model routing assumes an architect tier (Fable 5 / Opus 4.8 / GPT-5.6 Sol) for design and hard problems, and workhorse tiers (Sonnet 5 / Haiku 4.5 / Luna) for volume coding and runtime inference.

## The 50-Bet Table

| # | Name | Category | Target | Problem | Solution | Architect Model (Fable 5/Opus 4.8/GPT-5.6 Sol) | Workhorse Models (Sonnet 5/Haiku 4.5/Luna) | Cursor Workflow | Stack | Build Days | Setup A$ | Pricing | Y1 Mid Rev A$ | Success % | First Customer | Risk |
|---|------|----------|--------|---------|----------|------------------------------------------------|--------------------------------------------|-----------------|-------|-----------|----------|---------|---------------|-----------|----------------|------|
| 1 | QuoteMate | Tradie/NDIS | AU electricians/plumbers | Quotes take hours after site visits | Voice-note -> itemised PDF quote with margin rules | Fable 5 for quote-logic schema | Sonnet 5 build; Haiku 4.5 runtime parsing | Agent mode scaffold, Cmd+K refinements | Next.js, Supabase, Whisper, Stripe | 14 | 400 | A$49/mo | 8,000 | 55 | Local sparkie via Hipages groups | Tradies resist new software |
| 2 | NDIS NoteBot | Tradie/NDIS | NDIS support workers | Shift notes eat unpaid time | Voice -> compliant progress notes mapped to goals | Opus 4.8 for NDIS terminology mapping | Sonnet 5 build; Luna inference | Agent for CRUD, manual review of templates | Next.js, Postgres, Deepgram | 21 | 600 | A$29/user/mo | 12,000 | 50 | NDIS provider FB groups | Privacy Act sensitivity of health data |
| 3 | InvoiceChaser AI | AI Tools SMB | AU sole traders | Awkward chasing overdue invoices | Auto-drafted polite escalating reminders via Xero | Fable 5 for Xero OAuth design | Haiku 4.5 for email drafting at runtime | Cmd+K for API glue, agent for tests | Node, Xero API, Resend | 10 | 200 | A$19/mo | 5,000 | 60 | Xero app marketplace | Xero listing approval lag |
| 4 | TenderScan | Vertical AI Agents | SME govt-tender bidders | AusTender is a haystack | Daily agent scans, scores fit, drafts capability blurbs | GPT-5.6 Sol for scoring rubric | Sonnet 5 pipeline; Haiku 4.5 summarising | Agent scaffold, snippet library for scrapers | Python, Playwright, Postgres | 14 | 300 | A$99/mo | 15,000 | 45 | LinkedIn tender consultants | Tender data format changes |
| 5 | ReceptaCall | AI Receptionist | Solo allied-health clinics | Missed calls = missed bookings | AI answers, books into Cliniko, sends SMS confirms | Fable 5 for call-flow state machine | Luna for live voice turns | Agent build, manual test with Twilio sandbox | Twilio, Cliniko API, ElevenLabs | 21 | 800 | A$149/mo | 18,000 | 50 | Physio via referral | Voice latency hurting UX |
| 6 | ACL-Check | AI Compliance | AU ecommerce stores | Refund/warranty pages breach ACL | Scanner flags non-compliant policy wording, suggests fixes | Opus 4.8 for ACL rule encoding | Haiku 4.5 for page scanning | Cmd+K rule tweaks, agent for crawler | Python, FastAPI, Shopify app | 12 | 250 | A$39/mo | 6,000 | 45 | Shopify AU FB group | Not legal advice - disclaimers critical |
| 7 | LocalRank AI | AI Content+SEO | AU local service businesses | GMB posts and local content neglected | Auto-generates geo-targeted posts + suburb landing pages | Fable 5 for content architecture | Sonnet 5 gen; Haiku 4.5 variants | Agent mode with .cursorrules content style | Next.js, GMB API, OpenAI | 10 | 200 | A$59/mo | 9,000 | 55 | Local marketing agency white-label | Google spam-policy shifts |
| 8 | PRDraft | Dev Tools | Small dev teams | PR descriptions are lazy or missing | GitHub app writes structured PR descriptions + risk notes | Fable 5 for diff-analysis prompts | Haiku 4.5 per-PR runtime | Agent scaffold, dogfood on own repos | Node, GitHub App, Probot | 7 | 100 | US$10/repo/mo | 4,000 | 50 | Own network + HN launch | Crowded space, GitHub Copilot overlap |
| 9 | RosterGenie | Micro-SaaS Vertical | Cafes/hospitality AU | Rostering chaos + award compliance fear | AI roster builder respecting Hospitality Award rules | Opus 4.8 for award-rule engine | Sonnet 5 UI build | Agent for solver, manual verify edge cases | Next.js, Supabase, OR-tools | 25 | 500 | A$79/mo | 14,000 | 40 | Local cafe cluster | Fair Work rule updates |
| 10 | LeadSniper AU | Lead Gen | B2B service SMBs | Cold lists are stale and generic | Scrapes ABN registry + web signals, scores warm leads | Fable 5 for scoring model | Haiku 4.5 enrichment at scale | Agent pipeline, snippets for scrapers | Python, ABR API, Clay-style UI | 14 | 350 | A$149/mo | 16,000 | 45 | Own consultancy as case study | Scraping ToS / data hygiene |
| 11 | ChurnLens | Analytics | AU micro-SaaS founders | No idea why users churn | Plugs into Stripe+Posthog, AI writes weekly churn narratives | GPT-5.6 Sol for insight prompt design | Haiku 4.5 weekly report gen | Cmd+K for integrations, agent for dashboard | Next.js, Stripe API, PostHog | 12 | 200 | A$49/mo | 7,000 | 45 | Indie Hackers AU | Insight quality must beat dashboards |
| 12 | SiteSafe Docs | Tradie/NDIS | Builders/site supervisors | SWMS paperwork is painful | Photo + voice -> SWMS/JSA drafts per WHS templates | Opus 4.8 for WHS template logic | Sonnet 5 build; Luna extraction | Agent scaffold, PDF gen via snippets | React Native, Supabase | 21 | 600 | A$69/mo | 11,000 | 45 | Builder via trade association | Liability framing; docs need human sign-off |
| 13 | MenuTranslate | AI Localisation | AU tourism restaurants | Menus only in English | Photo menu -> CN/JP/KR translated menu with dietary tags | Fable 5 for layout reconstruction | Haiku 4.5 translation runtime | One-shot agent build | Next.js, GPT-4o vision | 7 | 100 | A$99 one-off + A$9/mo | 3,000 | 50 | Chinatown restaurants door-knock | Low ceiling, one-off heavy |
| 14 | FollowUpFox | AI Workflow | Mortgage brokers | Leads go cold between milestones | Automated milestone-aware nurture sequences | Fable 5 for lifecycle state design | Haiku 4.5 message drafting | Agent for CRM sync, manual QA sequences | Node, HubSpot API, Twilio | 14 | 300 | A$89/mo | 10,000 | 45 | Broker aggregator meetup | Spam Act consent handling |
| 15 | ReviewReply Pro | AI Tools SMB | Multi-location SMBs | Google reviews go unanswered | Tone-matched AI replies with owner approval queue | Fable 5 for tone system | Haiku 4.5 per-reply runtime | Cmd+K heavy, small codebase | Next.js, GMB API | 8 | 150 | A$29/location/mo | 6,000 | 55 | Franchise cafe group | GMB API access limits |
| 16 | GrantMatch AU | Vertical AI Agents | AU startups/SMBs | Grant landscape is opaque | Agent matches business profile to live grants, drafts EOIs | GPT-5.6 Sol for matching logic | Sonnet 5 crawler; Haiku 4.5 summaries | Agent pipeline, cache grant corpus | Python, Postgres, Next.js | 14 | 300 | A$79/mo | 9,000 | 40 | Accountant referral channel | Grant data freshness |
| 17 | PodClipper | AI Content+SEO | AU podcasters/coaches | Repurposing episodes takes hours | Episode -> clips, show notes, LinkedIn posts, SEO article | Fable 5 for repurposing pipeline | Sonnet 5 build; Haiku 4.5 gen | Agent scaffold, ffmpeg snippets | Python, Whisper, ffmpeg | 12 | 250 | A$39/mo | 7,000 | 50 | Business podcast hosts | Commoditised; differentiation via AU voice |
| 18 | EnvDoctor | Dev Tools | Dev teams onboarding juniors | "Works on my machine" onboarding pain | CLI diagnoses env drift, auto-fixes with explanations | Fable 5 for diagnosis heuristics | Sonnet 5 CLI build | Agent + heavy dogfooding | Rust or Go CLI | 14 | 100 | US$8/dev/mo | 4,000 | 40 | Own clients' dev teams | Endless env permutations |
| 19 | FormFiller NDIS | Tradie/NDIS | NDIS plan managers | Claim forms are repetitive | AI pre-fills claims from invoices + plan data | Opus 4.8 for claim-rule mapping | Haiku 4.5 extraction runtime | Agent for parsers, manual verify against PACE | Python, FastAPI, React | 21 | 500 | A$99/mo | 13,000 | 45 | Plan manager via NDIS expo | NDIA portal/API changes |
| 20 | HeatMap Local | Analytics | Real estate agents | No data-backed appraisal narratives | Suburb-level trend reports auto-generated per listing | Fable 5 for report structure | Haiku 4.5 narrative gen | Cmd+K for data joins, agent for PDF | Python, CoreLogic-alt data, Next.js | 14 | 400 | A$59/agent/mo | 8,000 | 40 | Boutique agency principal | Property data licensing cost |
| 21 | OnCallTriage | AI Receptionist | IT MSPs after-hours | After-hours calls burn on-call staff | AI triages severity, wakes humans only for P1s | Fable 5 for triage decision tree | Luna live voice; Haiku 4.5 ticket writes | Agent build, Twilio test harness | Twilio, ConnectWise API | 21 | 700 | A$199/mo | 17,000 | 45 | MSP peer network | Misclassified P1 = trust loss |
| 22 | PolicyPack | AI Compliance | AU startups pre-funding | Privacy policies are copy-pasted junk | Generates APP-aligned privacy policy + data register | Opus 4.8 for APP clause logic | Sonnet 5 wizard build | Agent scaffold, lawyer-reviewed templates | Next.js, Stripe | 10 | 800 (legal review) | A$299 one-off + A$19/mo updates | 6,000 | 45 | Startup accelerator cohorts | Must avoid legal-advice claims |
| 23 | AbandonRescue | AI Personalisation | Shopify AU stores | Generic abandoned-cart emails ignored | Per-customer AI emails referencing browsed items + tone | Fable 5 for personalisation strategy | Haiku 4.5 per-email runtime | Cmd+K for Shopify hooks | Shopify app, Node | 10 | 200 | A$0.05/email or A$49/mo | 8,000 | 50 | Shopify AU community | Deliverability management |
| 24 | ScopeGuard | AI Tools SMB | Freelance devs/designers | Scope creep kills margins | Analyses client emails, flags out-of-scope asks, drafts responses | GPT-5.6 Sol for scope-detection prompts | Haiku 4.5 email analysis | Small build, Cmd+K only | Chrome ext, Gmail API | 8 | 100 | A$15/mo | 3,000 | 40 | Freelancer subreddits | Email privacy trust barrier |
| 25 | VetVoice | AI Receptionist | Suburban vet clinics | Front desk overwhelmed | AI books appointments, answers FAQs, triages emergencies | Fable 5 for emergency triage rules | Luna voice; Haiku 4.5 FAQ | Agent + real clinic shadow testing | Twilio, ezyVet API | 25 | 900 | A$179/mo | 15,000 | 40 | Local vet via pet-owner intro | Animal emergency misrouting |
| 26 | BlogEngine AU | AI Content+SEO | Accounting/law firms | No time for content marketing | Monthly AU-regulation-aware article packs with review workflow | Opus 4.8 for accuracy guardrails | Sonnet 5 drafting | Agent pipeline, human-in-loop UI | Next.js, Supabase | 12 | 250 | A$199/mo | 12,000 | 45 | Accountant client upsell | Professional bodies' advertising rules |
| 27 | StackAudit | Dev Tools | CTOs of 5-20 person teams | Unknown dependency/licence risk | Repo scan -> licence, CVE, bus-factor report | Fable 5 for risk scoring | Sonnet 5 scanner build | Agent scaffold, test on OSS corpus | Go, GitHub API | 14 | 150 | A$99/scan or A$49/mo | 6,000 | 40 | Fractional CTO network | Snyk et al. overlap |
| 28 | BookingBridge | AI Workflow | Beauty/wellness salons | Double-entry across Fresha + socials | Unified inbox: DMs -> bookings automatically | Fable 5 for intent parsing design | Haiku 4.5 DM parsing runtime | Agent for integrations | Node, Meta API, Fresha API | 18 | 400 | A$69/mo | 9,000 | 40 | Salon via spouse/friend network | Meta API approval process |
| 29 | ColdEmail Local | Lead Gen | AU B2B agencies | Cold outreach sounds American | AU-idiom outreach engine with Spam Act compliance built in | Fable 5 for voice/persona system | Haiku 4.5 email gen | Cmd+K, snippet-driven | Node, Smartlead API | 10 | 200 | A$99/mo | 10,000 | 45 | Own outbound as proof | Deliverability + Spam Act edge cases |
| 30 | RetainRadar | Analytics | Gyms/studios AU | Member churn invisible until cancel | Attendance-pattern AI flags at-risk members, drafts win-backs | GPT-5.6 Sol for churn signals | Haiku 4.5 weekly runs | Agent for integrations | Python, Glofox/Mindbody API | 14 | 300 | A$79/mo | 8,000 | 40 | Local gym owner | Integration breadth needed |
| 31 | SubbyMatch | Service Platforms | Head contractors | Finding reliable subbies is word-of-mouth | Vetted subbie marketplace with AI capability matching | Fable 5 for matching + vetting design | Sonnet 5 marketplace build | Agent scaffold, seed data manually | Next.js, Supabase, Stripe Connect | 30 | 1,200 | 5% transaction fee | 10,000 | 30 | Builder contacts, seed 20 subbies | Chicken-and-egg liquidity |
| 32 | CareShift | Service Platforms | NDIS participants/families | Finding fill-in support workers is hard | Shift-fill marketplace with verified workers + AI matching | Opus 4.8 for screening/compliance flow | Sonnet 5 build | Agent + manual worker onboarding | Next.js, Supabase, Stripe | 30 | 1,500 | 8% booking fee | 12,000 | 30 | NDIS coordinator network | Worker screening liability |
| 33 | TranslateDocs AU | AI Localisation | Migration agents | Client documents need certified-style translation prep | AI first-pass translation + formatting for NAATI review | Fable 5 for document fidelity pipeline | Haiku 4.5 translation | Agent for doc parsing | Python, FastAPI | 12 | 200 | A$25/doc | 5,000 | 40 | Migration agent directory outreach | Cannot claim certified status |
| 34 | PitchPolish | AI Tools SMB | AU consultants | Proposals look amateur | Brand-consistent AI proposal builder from call notes | Fable 5 for proposal architecture | Sonnet 5 build; Haiku 4.5 drafting | Agent + own proposals as training set | Next.js, react-pdf | 10 | 150 | A$39/mo | 6,000 | 50 | Consultant peers | PandaDoc/Qwilr competition |
| 35 | SafetyMinutes | AI Compliance | SMB manufacturers | Toolbox-talk records patchy for audits | Voice-recorded talks -> WHS-compliant minutes + register | Opus 4.8 for WHS structure | Luna transcription; Haiku 4.5 formatting | Agent build, template snippets | React Native, Supabase | 14 | 350 | A$49/mo | 7,000 | 40 | Manufacturer via WHS consultant | Audit-defensibility expectations |
| 36 | UpsellIQ | AI Personalisation | AU ecommerce A$1-10M | Generic "you may also like" widgets | Behaviour + AU-season aware upsell recommendations | GPT-5.6 Sol for reco strategy | Haiku 4.5 real-time recos | Cmd+K for widget, agent for pipeline | Shopify app, edge functions | 14 | 300 | A$99/mo + 0.5% uplift | 11,000 | 40 | Shopify Plus AU agency partner | Attribution disputes |
| 37 | MeetingMiner | AI Workflow | Professional services firms | Action items vanish after meetings | Meeting audio -> CRM-logged actions with owner/due date | Fable 5 for extraction schema | Luna transcription; Haiku 4.5 extraction | Agent for CRM connectors | Node, Whisper, HubSpot | 10 | 200 | A$25/user/mo | 8,000 | 50 | Own client meetings as demo | Fireflies/Otter competition - win on CRM depth |
| 38 | AdCopy Lab AU | AI Content+SEO | AU PPC freelancers | Ad variants take too long | Bulk ACL-safe ad copy variants with claim checking | Opus 4.8 for claim-compliance checks | Haiku 4.5 variant gen | Small app, Cmd+K driven | Next.js, Google Ads API | 8 | 150 | A$49/mo | 5,000 | 45 | PPC Slack communities | Ad policy false positives |
| 39 | TestPilot | Dev Tools | Agencies inheriting legacy code | No tests on inherited codebases | AI generates characterisation test suites from behaviour | Fable 5 for test-strategy per codebase | Sonnet 5 test generation | Agent mode, verify via CI runs | Node/Python, GitHub Actions | 14 | 100 | A$499/codebase | 7,000 | 40 | Agencies in own network | Flaky generated tests |
| 40 | QuoteCompare NDIS | Tradie/NDIS | NDIS participants | Provider pricing is opaque | Compare provider quotes against NDIS price caps | Opus 4.8 for price-guide encoding | Haiku 4.5 quote parsing | Agent + annual price-guide update job | Next.js, Supabase | 12 | 250 | Free + A$99/mo provider listings | 6,000 | 35 | Participant advocacy groups | Two-sided adoption |
| 41 | ChatDocs Legal | AI Tools SMB | Suburban law firms | Precedent search is manual | Firm-private RAG over precedents with citation links | Fable 5 for RAG architecture | Luna embeddings; Haiku 4.5 answers | Agent scaffold, eval harness first | Python, pgvector, Next.js | 21 | 500 | A$149/mo | 13,000 | 40 | Law firm client referral | Confidentiality assurances (APP 11) |
| 42 | SurveySense | Analytics | HR consultants | Staff survey analysis is slow | Free-text survey responses -> themed insight reports | GPT-5.6 Sol for theming methodology | Haiku 4.5 batch analysis | Agent for pipeline, template reports | Python, Streamlit -> Next.js | 10 | 150 | A$199/survey | 6,000 | 45 | HR consultant partnership | Small-sample anonymity risks |
| 43 | ParcelPredict | Micro-SaaS Vertical | AU 3PL/ecommerce ops | Delivery-date promises are guesses | Carrier-history AI predicts realistic ETAs per postcode | Fable 5 for prediction approach | Sonnet 5 build; Haiku 4.5 serving | Agent + historical data backtest | Python, AusPost API | 18 | 400 | A$79/mo | 8,000 | 35 | 3PL contact from consulting | Carrier data access |
| 44 | OnboardOS | AI Workflow | AU SMBs hiring first staff | Onboarding is ad-hoc and non-compliant | Generates Fair-Work-aware onboarding checklists + docs | Opus 4.8 for employment doc logic | Sonnet 5 wizard | Agent scaffold, HR-advisor reviewed | Next.js, Supabase | 12 | 600 (HR review) | A$59/hire or A$39/mo | 6,000 | 40 | Bookkeeper referral channel | Employment law nuance |
| 45 | ReEngage Dental | AI Personalisation | Dental practices | Lapsed patients never return | Recall campaigns personalised by treatment history | Fable 5 for recall strategy | Haiku 4.5 message gen | Agent for PMS integration | Node, Dental4Windows API | 18 | 500 | A$129/mo | 12,000 | 40 | Dentist via own dentist | Health-data handling (APPs) |
| 46 | DevRetainer Bot | AI Receptionist | Freelance devs/agencies | Client "quick questions" interrupt deep work | AI triages client Slack/email, answers known questions | Fable 5 for knowledge-base design | Haiku 4.5 runtime answers | Cmd+K, dogfood on own clients | Slack app, Node | 10 | 150 | A$49/mo | 5,000 | 45 | Own consultancy clients | Wrong answers to clients |
| 47 | GreenAudit | Micro-SaaS Vertical | AU SMBs facing ESG asks | Enterprise customers demand carbon data | Simple emissions estimator + supplier-ready reports | GPT-5.6 Sol for estimation methodology | Sonnet 5 build | Agent + factor-database snippets | Next.js, Supabase | 14 | 300 | A$69/mo | 7,000 | 35 | SMB supplying big retail | Methodology credibility |
| 48 | ListingLift | AI Content+SEO | Real estate copywriters | Listing copy is repetitive | Photos + dot points -> styled listing copy in agency voice | Fable 5 for voice-matching system | Haiku 4.5 gen runtime | One-week Cmd+K build | Next.js, GPT-4o vision | 7 | 100 | A$99/mo/agency | 5,000 | 50 | Agency from idea #20 pipeline | Low switching cost |
| 49 | IncidentScribe | Dev Tools | SRE/on-call teams | Postmortems written days late or never | Slack + logs -> draft postmortem within an hour | Fable 5 for timeline reconstruction | Sonnet 5 build; Haiku 4.5 drafting | Agent scaffold, replay real incidents | Node, Slack API, Datadog API | 14 | 200 | US$49/mo | 6,000 | 40 | MSP + dev network | Log-source variability |
| 50 | KoalaKiosk | AI Localisation | AU tourism operators | International visitors get poor pre-visit info | Multilingual AI concierge widget for tour sites | Fable 5 for concierge flows | Haiku 4.5 multilingual chat | Agent build, embed widget | Next.js edge, widget JS | 10 | 200 | A$49/mo | 5,000 | 40 | Tourism operator association | Seasonal revenue |
| 51 | PayrollSanity | AI Compliance | Bookkeepers | Award misclassification anxiety | Cross-checks payroll runs against modern-award rates | Opus 4.8 for award-rate engine | Haiku 4.5 batch checks | Agent + curated award dataset | Python, Xero Payroll API | 21 | 500 | A$89/mo | 10,000 | 35 | Bookkeeper association webinar | Award interpretation liability |
| 52 | WaitlistWhisper | Lead Gen | New AU product launches | Waitlists go cold before launch | AI-personalised waitlist nurture + launch sequencing | Fable 5 for sequence strategy | Haiku 4.5 email gen | Small build, Cmd+K | Node, Resend, Supabase | 8 | 100 | A$29/mo | 4,000 | 45 | Indie founders on X/LinkedIn | Tiny wedge; must expand |

**Blended portfolio success estimate: ~43%** (weighted across 52 bets, each >=30%).

## Top 10 Picks

1. **QuoteMate (#1)** - Scaffold voice->quote pipeline in agent mode with Fable 5 designing the quote schema, ship PDF export by day 7, pilot with one electrician by day 14. Start with **Fable 5**, hand volume coding to Sonnet 5.
2. **ReceptaCall (#5)** - Build the Twilio call-flow state machine first (Fable 5), wire Cliniko booking, run 50 test calls before the first clinic. Start with **Fable 5**.
3. **InvoiceChaser AI (#3)** - One-week build: Xero OAuth + reminder engine via Cmd+K, launch on the Xero marketplace. Start with **Sonnet 5** (simple enough), escalate only if OAuth gets hairy.
4. **TenderScan (#4)** - Agent-built AusTender crawler + GPT-5.6 Sol scoring rubric, dogfood by bidding on a real tender in week 2. Start with **GPT-5.6 Sol** for the rubric.
5. **NDIS NoteBot (#2)** - Opus 4.8 encodes NDIS goal-mapping, Sonnet 5 builds the mobile-first UI, pilot with two support workers under a privacy-first data agreement. Start with **Opus 4.8**.
6. **LeadSniper AU (#10)** - Build the ABR-enrichment pipeline, use your own consultancy's outbound as the proving ground before selling. Start with **Fable 5** for scoring design.
7. **LocalRank AI (#7)** - Content-architecture prompt system in Fable 5, then pure Haiku 4.5 generation; white-label to one agency in week 2. Start with **Fable 5**.
8. **PolicyPack (#22)** - Opus 4.8 drafts APP clause logic, pay a lawyer once (~A$800) to review templates, then sell A$299 packs through accelerators. Start with **Opus 4.8**.
9. **MeetingMiner (#37)** - Whisper/Luna transcription + Haiku extraction into HubSpot; demo it in your own client meetings from day 3. Start with **Fable 5** for the extraction schema, then coast on Haiku 4.5.
10. **PRDraft (#8)** - Seven-day GitHub App build, dogfood on every repo you own, launch publicly for distribution learning even if revenue stays modest. Start with **Sonnet 5**.

## 4-Tier Model Routing Pattern

| Tier | Model | Use for | Rule of thumb |
|------|-------|---------|---------------|
| 1 - Architect | **Fable 5** | System design, novel algorithms, tricky state machines, debugging that has stumped Tier 2 twice | Invoke deliberately, never by default; one deep session beats ten shallow ones |
| 2 - Heavy reasoning | **Opus 4.8** | Domain-rule encoding (awards, NDIS, ACL, APPs), long-context refactors, security-sensitive code | When correctness of *rules* matters more than speed |
| 3 - Workhorse | **Sonnet 5** | 80% of feature coding, CRUD, integrations, tests, UI | Default coding model; escalate up only after two failed attempts |
| 4 - Volume | **Haiku 4.5 / Luna** | Runtime inference (drafting, parsing, classification), boilerplate, renames, docstrings, commit messages | Anything you'd trust a fast junior with; always first choice for per-request product inference to protect margins |

**Escalation rule:** start one tier lower than you think you need; escalate on failure, never pre-emptively. **De-escalation rule:** once the architect has produced a spec, everything downstream runs at Tier 3-4.

## Token-Saving Cheat Sheet

- **Cmd+K for ~70% of edits.** Inline edits use a fraction of the context of agent chats. Reserve agent mode for multi-file work.
- **Scope context ruthlessly.** Reference specific files (`@file`) instead of `@codebase`; every unneeded file in context is wasted spend.
- **Snippet library.** Keep reusable snippets (auth, Stripe, Supabase client, PDF gen, Twilio handlers) in a `snippets/` repo - paste, don't regenerate.
- **Cache hits.** Keep system prompts and `.cursorrules` stable across a session; changing them invalidates prompt caches. Batch similar tasks together so cached context is reused.
- **Spec once, execute cheap.** Have the architect model produce a written plan, then feed that plan to Sonnet/Haiku - never re-derive the design.
- **Runtime frugality.** In shipped products, route to Haiku 4.5/Luna by default and cache common responses (FAQ answers, template sections) so recurring cost stays under A$500/mo.

## Continuous Testing Loop

`BUILD -> TEST -> VERIFY -> ITERATE`   (max 5 cycles per feature)

1. **Build** - smallest testable slice (one endpoint, one screen, one prompt chain).
2. **Test** - run it end-to-end: automated test + one real-world input (an actual quote, call recording, or invoice).
3. **Verify** - check output against explicit acceptance criteria written *before* the build; for AI outputs, spot-check 10 samples for accuracy and tone.
4. **Iterate** - fix the top failure only, then loop.
5. **Circuit breaker** - if 5 cycles don't reach acceptance, stop: escalate to the architect tier for a redesign or kill the feature. Never grind past cycle 5 at the workhorse tier.

## `.cursorrules` Template

```text
# .cursorrules - AU micro-SaaS defaults

## Stack
- Next.js (App Router) + TypeScript strict; Supabase (Postgres + RLS); Tailwind; Stripe for billing.
- Prefer server components; API routes only when necessary.

## Code style
- Small, single-purpose functions. No premature abstraction.
- Zod validation at every external boundary (user input, webhooks, third-party APIs).
- Errors: fail loudly in dev, degrade gracefully in prod, always log with context.

## AI features
- All LLM calls go through /lib/ai/client.ts - never inline API calls.
- Default model: cheapest that passes evals (Haiku 4.5 / Luna). Document any escalation.
- Every prompt has a versioned file in /prompts with expected-output examples.

## Compliance (Australia)
- Privacy Act 1988 / APPs: collect minimum data; document purpose per field; delete-on-request path required.
- Australian Consumer Law: no misleading claims in generated copy; refunds honour statutory guarantees.
- Health/NDIS data: encrypt at rest, AU-region hosting, no data in prompts to third-party models without de-identification.
- Spam Act 2003: consent + working unsubscribe on every outbound message feature.

## Testing
- Every feature ships with at least one happy-path test and one failure-path test.
- AI outputs need an eval file with 5+ graded examples before merge.

## Never
- Never commit secrets. Never bypass RLS. Never claim legal/financial advice in UI copy.
```

## Cursor Pro Power-User Tips

1. **Plan in chat, execute in Cmd+K.** Use one agent conversation to produce a numbered implementation plan, then execute each step as a targeted inline edit - you get architect-quality direction at workhorse cost.
2. **Maintain per-project `.cursorrules` from day one.** The compliance and stack constraints above prevent the model from re-asking or re-deciding, saving tokens and review time on every session.
3. **Use `@file` and `@docs` pins instead of letting the agent search.** Pinning the two files that matter beats codebase-wide retrieval for both accuracy and cost.
4. **Keep an evals folder and run it after every AI-prompt change.** Ten graded examples per prompt catches regressions that manual spot-checks miss, and doubles as your demo material for customers.
5. **Dogfood distribution: build each product's first landing page and outreach emails inside the same Cursor session.** The model already has full product context - marketing copy generated there is sharper than starting a fresh session.
