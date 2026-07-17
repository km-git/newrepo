# Cursor v4 Frontier Discovery — AU Micro-SaaS / AI Tools Portfolio
**Date:** July 17, 2026 | **Operator:** 1-2 person AU firm (ABN/ACN) | **Y1 target:** A$220K (1p) / A$330K (2p) | **Bets:** 56 | **Cost ceiling:** A$5K/MVP | **Build ceiling:** 7-30 days

---

## 1. Business Idea Table (56 Ideas, 14 Categories)

| # | Name | Category | Target | Problem | Solution | Architect Model | Workhorse Models | Cursor Workflow | Stack | Build Days | Setup A$ | Pricing | Y1 Mid Rev A$ | Success % | First Customer | Risk |
|---|------|----------|--------|---------|----------|-----------------|------------------|-----------------|-------|-----------|----------|---------|---------------|-----------|----------------|------|
| 1 | QuoteDraft AI | AI Tools SMB | AU trade/service SMBs | Quotes take hours, lost jobs | Voice/photo notes to branded PDF quote | Fable 5 | Sonnet 5 + Haiku 4.5 | Max Mode plan; Cmd+K edits; BugBot PR | Next.js+Supabase+Stripe | 14 | 800 | A$39/mo | 28K | 35 | Local trade FB groups | Free tools compete |
| 2 | InboxTriage | AI Tools SMB | SMB owner-operators | Email overload, missed leads | AI triage, priority + draft replies | GPT-5.6 Sol | Sonnet 5 + Luna | Composer scaffold; Cmd+K refine | Next.js+Gmail API+Supabase | 12 | 500 | A$29/mo | 20K | 30 | Bookkeeper referrals | Gmail API review delay |
| 3 | ReviewResponder | AI Tools SMB | Local AU SMBs | Google reviews ignored | Auto-draft on-brand review replies | Opus 4.8 | Haiku 4.5 | Auto mode; snippets for prompts | Next.js+GBP API+Stripe | 8 | 300 | A$19/mo | 14K | 35 | Café/salon walk-ins | Low ACV |
| 4 | MeetingMinute | AI Tools SMB | SMB teams on Teams/Zoom | Minutes never written | Transcript to minutes + actions | Opus 4.8 | Sonnet 5 + Haiku 4.5 | Plan; Cmd+K; BugBot | Next.js+Whisper+Supabase | 12 | 600 | A$25/user/mo | 22K | 30 | AI consulting clients | Crowded space |
| 5 | StrataNote | Micro-SaaS Vertical | Strata managers/committees | Manual minutes + compliance chasing | Minutes, motions, by-law reminder tracker | Fable 5 | Sonnet 5 | Max Mode schema; Cmd+K UI | Next.js+Supabase+Resend | 18 | 900 | A$59/scheme/mo | 32K | 30 | Strata manager LinkedIn | Niche sales cycle |
| 6 | PoolCertPro | Micro-SaaS Vertical | Pool safety certifiers | Paper inspection reports | Mobile checklist to compliant PDF report | Opus 4.8 | Sonnet 5 + Haiku 4.5 | Composer PWA; BugBot | PWA+Supabase+Stripe | 14 | 500 | A$49/mo | 18K | 30 | QLD certifier assoc. list | Small market |
| 7 | AgistMate | Micro-SaaS Vertical | Horse agistment operators | Spreadsheet billing chaos | Bookings, billing, paddock roster | GPT-5.6 Sol | Sonnet 5 | Auto mode CRUD; Cmd+K | Next.js+Supabase+Stripe | 14 | 400 | A$45/mo | 15K | 25 | Rural FB groups | Tiny TAM |
| 8 | CafeRoster | Micro-SaaS Vertical | AU cafés 5-20 staff | Award complexity in rosters | Roster builder w/ award-rate cost hints (not advice) | Fable 5 | Sonnet 5 + Luna | Max Mode rules engine; tests-first | Next.js+Supabase | 25 | 1200 | A$69/mo | 30K | 25 | Local café owners | Award data upkeep |
| 9 | TenderScout | Vertical AI Agents | SMBs bidding govt work | AusTender monitoring is tedious | Agent scans tenders, scores fit, drafts summary | Fable 5 | Sonnet 5 + Haiku 4.5 | Max Mode agent loop; eval snippets | Python+Postgres+Next.js | 18 | 800 | A$99/mo | 40K | 35 | Consulting network | Source format changes |
| 10 | GrantsAgentAU | Vertical AI Agents | AU SMBs/nonprofits | Grants missed constantly | Agent matches grants to business profile, alerts | GPT-5.6 Sol | Sonnet 5 + Luna | Composer pipeline; cache prompts | Python+Supabase+Resend | 15 | 600 | A$49/mo | 30K | 35 | Accountant partners | Data freshness |
| 11 | FreightQuoteAgent | Vertical AI Agents | Freight brokers/3PLs | Email quote requests pile up | Agent parses enquiry, drafts rated quote | Fable 5 | Sonnet 5 | Plan extraction schema; BugBot | Python+Next.js+Supabase | 20 | 1000 | A$149/mo | 45K | 30 | Broker cold email | Rate-card integration |
| 12 | RealtyFollowUp | Vertical AI Agents | Real estate agencies | Open-home leads go cold | Agent sequences SMS/email follow-ups | Opus 4.8 | Sonnet 5 + Haiku 4.5 | Auto mode; Cmd+K copy tuning | Next.js+Twilio+Supabase | 14 | 700 | A$129/office/mo | 35K | 30 | Local agency principal | Spam compliance |
| 13 | LocalRankKit | AI Content+SEO | Tradies wanting leads | No suburb landing pages | Generates suburb x service SEO pages | Opus 4.8 | Haiku 4.5 + Luna | Auto mode templates; snippets | Next.js+Vercel+Stripe | 10 | 400 | A$49/mo | 26K | 35 | Existing tradie clients | Google algo shifts |
| 14 | CaseStudyForge | AI Content+SEO | Trades/agencies | Job photos never marketed | Photos+notes to case study page/post | Opus 4.8 | Sonnet 5 | Cmd+K heavy; image pipeline plan | Next.js+S3+Stripe | 10 | 400 | A$29/mo | 16K | 30 | Trade FB groups | Low urgency |
| 15 | GBPPostBot | AI Content+SEO | Local SMBs | Google profile goes stale | Weekly auto-drafted GBP posts | GPT-5.6 Sol | Haiku 4.5 | Auto mode; prompt snippets | Next.js+GBP API | 8 | 300 | A$15/mo | 12K | 30 | Salon/café outreach | API quota limits |
| 16 | FAQMiner | AI Content+SEO | SMBs w/ support inboxes | FAQ content untapped | Mines emails to SEO FAQ/schema pages | Opus 4.8 | Sonnet 5 + Luna | Composer ETL; Cmd+K | Python+Next.js+Supabase | 12 | 500 | A$39/mo | 18K | 30 | Agency white-label | Data access friction |
| 17 | SchemaDiff Sentinel | Dev Tools | Teams on Postgres | Risky migrations slip through | CI check flags destructive schema diffs | Fable 5 | Sonnet 5 + Haiku 4.5 | Tests-first; Max Mode edge cases | Go/Python+GitHub Action | 15 | 200 | A$29/repo/mo | 22K | 30 | Dev communities, HN | OSS competition |
| 18 | EnvAudit | Dev Tools | SaaS dev teams | Secrets/env drift undocumented | Scans repos, flags env hygiene issues | Opus 4.8 | Haiku 4.5 | Auto mode CLI; BugBot | Node CLI+GitHub App | 10 | 200 | A$19/repo/mo | 14K | 25 | Cursor/dev Discords | Freebie expectation |
| 19 | PromptPack CLI | Dev Tools | AI dev teams | Prompts unversioned, scattered | Versioned prompt/snippet library + diff | GPT-5.6 Sol | Sonnet 5 + Luna | Composer CLI; dogfood daily | Node CLI+Supabase | 12 | 300 | A$15/user/mo | 18K | 30 | Own network, X/dev blogs | Fast-moving space |
| 20 | FlakyFinder | Dev Tools | CI-heavy teams | Flaky tests waste hours | Analyses CI history, ranks flaky tests | Fable 5 | Sonnet 5 | Max Mode stats logic; tests-first | Python+GitHub Action | 16 | 300 | A$49/mo | 20K | 25 | GitHub Marketplace | CI vendor variety |
| 21 | DocToWorkflow | AI Workflow | Ops-heavy SMBs | SOPs sit unread in docs | Converts SOP docs to assigned checklists | Opus 4.8 | Sonnet 5 + Haiku 4.5 | Plan parser; Cmd+K UI | Next.js+Supabase | 14 | 500 | A$49/mo | 24K | 30 | Ops consultants | Change management |
| 22 | ChaseInvoice | AI Workflow | AU SMBs w/ Xero | Late payments hurt cashflow | Polite AU-tone AR chasing sequences | GPT-5.6 Sol | Haiku 4.5 | Auto mode; Xero SDK snippets | Next.js+Xero API+Stripe | 10 | 400 | A$29/mo | 26K | 40 | Xero advisor directory listing | Xero app approval |
| 23 | OnboardFlow | AI Workflow | Digital agencies | Client onboarding is ad hoc | Generates branded onboarding portals | Opus 4.8 | Sonnet 5 | Composer scaffold; Cmd+K theming | Next.js+Supabase+Stripe | 14 | 500 | A$59/mo | 22K | 30 | Agency owner communities | Portal fatigue |
| 24 | HandoverHero | AI Workflow | Clinics/care teams | Shift handovers lossy | Structured handover notes + task carry-over | Fable 5 | Sonnet 5 + Haiku 4.5 | Max Mode data model; privacy review | Next.js+Supabase (AU region) | 20 | 800 | A$79/site/mo | 28K | 25 | Allied health contacts | Privacy sensitivity |
| 25 | ABNLeads | Lead Gen | B2B service sellers | New businesses hard to find early | Alerts on new ABN registrations by industry/region | GPT-5.6 Sol | Haiku 4.5 + Luna | Composer ETL; cron plan | Python+Postgres+Next.js | 12 | 400 | A$59/mo | 30K | 35 | Insurance brokers, accountants | Data licence terms |
| 26 | CouncilDA Leads | Lead Gen | Builders/trades | DA approvals = future jobs | Monitors council DA feeds, alerts matching trades | Fable 5 | Sonnet 5 + Luna | Max Mode scraper design; retries | Python+Supabase+Resend | 18 | 700 | A$79/mo | 36K | 35 | Builder network | Council site changes |
| 27 | QuoteRescue | Lead Gen | Trades/services | Sent quotes never chased | Auto follow-up sequences on unaccepted quotes | Opus 4.8 | Haiku 4.5 | Auto mode; Cmd+K sequences | Next.js+Twilio+Supabase | 10 | 400 | A$39/mo | 24K | 40 | QuoteDraft cross-sell | SMS costs |
| 28 | OutreachDraft | Lead Gen | B2B consultants | Generic outreach ignored | AI-personalised first-line drafts from public info | GPT-5.6 Sol | Sonnet 5 | Snippets library; Auto mode | Next.js+Supabase | 8 | 300 | A$49/mo | 18K | 25 | Own outreach as demo | Platform ToS shifts |
| 29 | TradieMetrics | Analytics | Trade businesses 2-15 staff | No job profitability visibility | Xero + job data to margin dashboard | Fable 5 | Sonnet 5 + Haiku 4.5 | Max Mode data model; chart snippets | Next.js+Xero API+Postgres | 20 | 900 | A$79/mo | 34K | 30 | Trade bookkeepers | Data mapping effort |
| 30 | NDISUtil | Analytics | NDIS providers | Plan utilisation opaque | Utilisation/budget-burn dashboard (aggregate, no participant PII) | Fable 5 | Sonnet 5 | Plan privacy-first schema; tests | Next.js+Supabase (AU) | 22 | 1000 | A$99/mo | 38K | 30 | NDIS provider meetups | PII boundary discipline |
| 31 | ShopfrontStats | Analytics | AU retailers | POS data unused | Sales trend + weather/event overlay insights | Opus 4.8 | Sonnet 5 + Luna | Composer connectors; Cmd+K | Next.js+Square API+Postgres | 16 | 600 | A$49/mo | 20K | 25 | Local retail strip | POS API variety |
| 32 | ChurnSignal | Analytics | Micro-SaaS founders | Churn discovered too late | Usage-drop early-warning alerts | GPT-5.6 Sol | Haiku 4.5 | Auto mode; dogfood on portfolio | Node+Postgres+Resend | 10 | 300 | A$29/mo | 15K | 25 | Indie hacker communities | DIY substitutes |
| 33 | BookAClean | Service Platforms | Cleaning businesses | Booking + invoicing juggled | Client booking, recurring jobs, invoicing | Opus 4.8 | Sonnet 5 + Haiku 4.5 | Composer CRUD; BugBot | Next.js+Supabase+Stripe | 18 | 700 | A$59/mo | 26K | 30 | Cleaning FB groups | Incumbent apps |
| 34 | TradieSubbie | Service Platforms | Builders + subbies | Subbie availability unknown | Availability board + job match alerts | GPT-5.6 Sol | Sonnet 5 | Auto mode; Cmd+K mobile UI | Next.js+Supabase+Twilio | 16 | 600 | A$49/mo both sides | 24K | 25 | Builder contacts | Two-sided cold start |
| 35 | YardCrew | Service Platforms | Lawn/garden operators | Recurring runs on paper | Round scheduling, routes, auto-invoice | Opus 4.8 | Haiku 4.5 | Auto mode; maps snippet | Next.js+Supabase+Stripe | 14 | 500 | A$45/mo | 20K | 30 | Mowing FB groups | Seasonality |
| 36 | TherapyRoomShare | Service Platforms | Allied health clinics | Rooms sit empty | Room listing + booking between practitioners | Fable 5 | Sonnet 5 | Max Mode booking logic; tests | Next.js+Supabase+Stripe | 20 | 800 | 8% booking fee | 22K | 25 | Clinic owner contacts | Liquidity risk |
| 37 | SWMS Builder | Tradie/NDIS | AU construction trades | SWMS paperwork dreaded | Template-driven SWMS generator (not legal advice) | Fable 5 | Sonnet 5 + Haiku 4.5 | Max Mode template engine; disclaimers | Next.js+Supabase+Stripe | 14 | 600 | A$29/mo | 30K | 40 | Builder inductions, FB groups | Advice-line risk |
| 38 | NDIS AuditPrep | Tradie/NDIS | NDIS providers | Audit prep is panic-driven | Self-assessment vs Practice Standards, evidence checklist | Fable 5 | Sonnet 5 | Plan standards mapping; review loops | Next.js+Supabase (AU) | 20 | 900 | A$99/mo | 42K | 35 | NDIS consultant partners | Standards updates |
| 39 | VariationVault | Tradie/NDIS | Builders/renovators | Contract variations undocumented | Photo+note variation log, client sign-off | Opus 4.8 | Sonnet 5 + Haiku 4.5 | Composer PWA; Cmd+K | PWA+Supabase+Stripe | 12 | 500 | A$39/mo | 24K | 35 | Existing tradie software users | Habit change |
| 40 | ToolTrack | Tradie/NDIS | Trade crews | Tools lost/stolen untracked | QR tool register + theft report pack | Opus 4.8 | Haiku 4.5 | Auto mode; QR snippet | PWA+Supabase | 10 | 400 | A$25/mo | 16K | 30 | Trade suppliers counter | Low urgency |
| 41 | TradieDesk | AI Receptionist | Solo tradies | Missed calls = lost jobs | AI answers, qualifies, books jobs | Fable 5 | Sonnet 5 + Haiku 4.5 | Max Mode call flow; eval transcripts | Twilio Voice+LLM+Supabase | 21 | 1200 | A$99/mo | 48K | 40 | Tradie network + FB groups | Voice latency/quality |
| 42 | ClinicFrontDesk | AI Receptionist | Allied health clinics | After-hours calls unanswered | AI books appointments (no clinical advice) | Fable 5 | Sonnet 5 | Plan guardrails; scripted evals | Twilio+LLM+Cliniko API | 25 | 1500 | A$149/mo | 45K | 30 | Physio/chiro contacts | Guardrail failures |
| 43 | SparkyCallback | AI Receptionist | Electricians/plumbers | Missed calls not followed up | Missed-call text-back + qualify chatbot | Opus 4.8 | Haiku 4.5 | Auto mode; Cmd+K flows | Twilio SMS+Next.js | 8 | 400 | A$49/mo | 26K | 40 | TradieDesk downsell | Carrier filtering |
| 44 | VetLineAI | AI Receptionist | Vet clinics | Phones ring out at peak | AI receptionist for bookings/triage-to-human | GPT-5.6 Sol | Sonnet 5 + Luna | Composer flows; transcript evals | Twilio+LLM+Supabase | 22 | 1200 | A$129/mo | 34K | 25 | Local vet visits | Advice-boundary risk |
| 45 | PrivacyPolicyAU | AI Compliance | AU SMB websites | Privacy Act changes missed | Policy generator + change alerts (not legal advice) | Opus 4.8 | Sonnet 5 + Haiku 4.5 | Plan template logic; disclaimers | Next.js+Supabase+Stripe | 10 | 400 | A$19/mo | 22K | 35 | Web agencies white-label | Advice-line risk |
| 46 | WHSInductor | AI Compliance | Construction/manufacturing SMBs | Paper inductions unauditable | Site induction builder + digital records | Opus 4.8 | Sonnet 5 | Composer forms; Cmd+K | Next.js+Supabase | 14 | 500 | A$59/site/mo | 26K | 30 | SWMS Builder cross-sell | Content upkeep |
| 47 | FoodSafeLog | AI Compliance | Cafés/restaurants | Paper temp logs fail audits | Digital food-safety logs + reminders | GPT-5.6 Sol | Haiku 4.5 | Auto mode PWA; offline plan | PWA+Supabase | 12 | 400 | A$35/mo | 20K | 30 | Council EHO networks, cafés | Kitchen adoption |
| 48 | ACLRefundFlow | AI Compliance | AU e-comm SMBs | Refund handling risks ACL breaches | Guided refund/remedy workflow templates (guidance only) | Fable 5 | Sonnet 5 | Max Mode decision tree; review | Next.js+Shopify API | 14 | 500 | A$39/mo | 18K | 25 | Shopify agency partners | Advice-line risk |
| 49 | AussieTone | AI Localisation | Inbound SaaS/agencies | US copy jars AU buyers | Localises copy: AU English, GST, formats | Opus 4.8 | Haiku 4.5 + Luna | Auto mode; style-guide snippets | Next.js+LLM API | 7 | 200 | A$29/mo + credits | 14K | 25 | Agency partners | Thin moat |
| 50 | MenuTranslate | AI Localisation | AU restaurants | Multilingual diners underserved | Menu to CN/JP/KR/VN with QR menu page | GPT-5.6 Sol | Haiku 4.5 | Auto mode; Cmd+K layouts | Next.js+LLM+Stripe | 8 | 300 | A$99 one-off + A$10/mo | 12K | 25 | Restaurant strip walk-ins | One-off heavy |
| 51 | NDIS EasyRead | AI Localisation | NDIS providers | Docs inaccessible to participants | Converts docs to Easy Read/plain language drafts | Fable 5 | Sonnet 5 | Plan style rules; human-review step | Next.js+LLM+Supabase | 12 | 400 | A$49/mo | 20K | 30 | NDIS AuditPrep cross-sell | Quality bar high |
| 52 | MultiQuote | AI Localisation | Trades in multicultural areas | Language barrier loses jobs | Translated quotes/invoices w/ AU trade terms | Opus 4.8 | Haiku 4.5 | Auto mode; template snippets | Next.js+LLM+Stripe | 8 | 300 | A$19/mo | 10K | 25 | QuoteDraft cross-sell | Small wedge |
| 53 | EmailPersona | AI Personalisation | AU e-comm stores | Generic email blasts underperform | Personalised email blocks from purchase history | GPT-5.6 Sol | Sonnet 5 + Luna | Composer Klaviyo hook; A/B plan | Node+Klaviyo API+Supabase | 15 | 600 | A$79/mo | 28K | 25 | Shopify agencies | ESP feature creep |
| 54 | CoursePath | AI Personalisation | Course creators | One-size lessons cause churn | Adaptive lesson sequencing per learner | Fable 5 | Sonnet 5 | Max Mode sequencing logic; evals | Next.js+Supabase+LLM | 20 | 700 | A$59/mo | 22K | 25 | Creator communities | Integration spread |
| 55 | GiftGenie | AI Personalisation | AU gift retailers | Shoppers overwhelmed, bounce | Quiz-driven gift recommender widget | Opus 4.8 | Haiku 4.5 | Auto mode widget; Cmd+K | JS widget+Next.js+Stripe | 10 | 400 | A$49/mo | 16K | 25 | Local gift shops pre-Xmas | Seasonal spikes |
| 56 | ProposalTailor | AI Personalisation | Agencies/consultants | Proposals rewritten from scratch | Personalised proposals from CRM notes + wins library | GPT-5.6 Sol | Sonnet 5 + Haiku 4.5 | Composer doc engine; snippets | Next.js+Supabase+Stripe | 14 | 500 | A$69/mo | 26K | 30 | Own consulting proposals as demo | Template leakage |

---

## 2. Top 10 Picks

Ranked by blended score (success % x revenue x build speed x distribution fit with existing tradie/NDIS network):

1. **TradieDesk (#41)** — Build Twilio voice loop + booking calendar + qualification script; dogfood on own missed calls first. Start with **Fable 5** (call-flow state machine is the hard part), hand UI to Sonnet 5.
2. **NDIS AuditPrep (#38)** — Map NDIS Practice Standards to a self-assessment checklist engine with evidence uploads. Start with **Fable 5** for standards-to-schema mapping, then Sonnet 5 for CRUD.
3. **SWMS Builder (#37)** — Template engine + trade-specific hazard libraries + PDF export with disclaimers. Start with **Fable 5** for the template/rules engine, Haiku 4.5 for form UI grind.
4. **ChaseInvoice (#22)** — Xero OAuth + overdue-invoice poller + AU-tone email/SMS sequences. Start with **GPT-5.6 Sol** for the Xero integration plan, Haiku 4.5 for sequence copy variants.
5. **CouncilDA Leads (#26)** — Scrapers/feeds for 10 high-volume councils, match rules, daily digest email. Start with **Fable 5** for resilient scraper architecture, Luna for per-council adapters.
6. **TenderScout (#9)** — AusTender ingestion + fit-scoring agent + weekly digest. Start with **Fable 5** for scoring rubric + agent loop, Sonnet 5 for pipeline plumbing.
7. **SparkyCallback (#43)** — Missed-call webhook, instant SMS-back, 3-question qualify bot. Start with **Opus 4.8** end-to-end; ship in ~8 days; upsell path to TradieDesk.
8. **QuoteDraft AI (#1)** — Voice note -> structured job -> branded PDF quote -> send/track. Start with **Fable 5** for extraction schema, Sonnet 5 for PDF/UI.
9. **ABNLeads (#25)** — Ingest new-registration data, filter by industry/region, alert digests. Start with **GPT-5.6 Sol** for ETL design, Haiku 4.5 for filters/UI.
10. **PrivacyPolicyAU (#45)** — Questionnaire -> policy generator -> monitored change alerts. Start with **Opus 4.8** for template logic + disclaimer framing, Haiku 4.5 for the wizard UI.

Portfolio note: picks 1, 3, 7, 8 share the tradie distribution channel; 2 shares NDIS channel — cross-sell compounds the 2.5% rule.

---

## 3. Four-Tier Model Routing Pattern

| Tier | Models | Use For | Don't Use For |
|------|--------|---------|---------------|
| **1 Frontier** | Fable 5, Opus 4.8, GPT-5.6 Sol | Architecture, data models, agent loops, gnarly debugging, security review, compliance-sensitive logic | Boilerplate, CSS, renames — burns budget |
| **2 Balanced** | Sonnet 5, Sonnet 4.6, Opus 4.5-4.7, GPT-5.6 Terra, GPT-5.5, Gemini 3.1 Pro | Feature implementation from a written plan, API integrations, moderate refactors, test writing | Novel architecture decisions |
| **3 Workhorse** | Haiku 4.5, GPT-5.6 Luna, Gemini 3.5 Flash, Grok 4.5, DeepSeek V3/R1 | CRUD, forms, copy variants, migrations, repetitive edits, commit messages | Anything ambiguous or multi-file-subtle |
| **4 Cursor-native** | Auto mode, Max Mode, Composer, BugBot | Auto: default daily driver. Max Mode: whole-repo reasoning (sparingly). Composer: multi-file scaffolds. BugBot: every PR before merge | Max Mode as default (token drain) |

**Routing rules of thumb:**
- Start every MVP with ONE Tier 1 session that produces `PLAN.md` (schema, routes, risks). Everything after executes against that plan on Tier 2/3.
- Escalate up a tier only after 2 failed attempts at the current tier; de-escalate when the plan is stable.
- Fable 5 for stateful/agentic logic; Opus 4.8 for careful full-stack builds and compliance wording; GPT-5.6 Sol for integration-heavy ETL and API work.
- Target spend split: ~10% Tier 1 / 40% Tier 2 / 50% Tier 3.

---

## 4. Token-Saving Cheat Sheet

| Technique | Saving | How |
|-----------|--------|-----|
| Cmd+K inline edits | ~70% vs chat | Select code, describe the change; skips full-context chat round-trips. Use for any single-file, single-intent edit. |
| Plan-then-execute | ~50% on Tier 1 | One frontier session writes `PLAN.md`; workhorses execute. Never re-explain the project mid-thread. |
| Prompt snippets library | ~30% per prompt | Keep reusable snippets (stack conventions, test template, PR checklist) — paste instead of re-typing context. |
| Cache hits | ~40-90% on input tokens | Keep long stable context (rules, schema) at the TOP of prompts, variable parts at the bottom; reuse the same thread for related edits so prefixes cache. |
| Scoped @-mentions | ~60% context | `@file`/`@folder` only what's needed; never "look at my whole codebase". |
| Fresh threads | Avoids bloat | Start a new chat per feature; long threads re-send history every turn. |
| Auto mode default | Budget stretch | Let Cursor route; reserve named frontier models for the 10% that matters. |
| .cursorrules | Free context | Conventions live in rules, not in every prompt. |

---

## 5. Continuous Testing Loop (max 5 cycles per outcome)

```
BUILD -> TEST -> VERIFY ISC -> ITERATE
```

1. **Build**: Implement against `PLAN.md`. One feature slice per cycle. Workhorse/balanced models.
2. **Test**: Run the automated suite + one manual end-to-end pass of the exact user journey (e.g. missed call -> SMS -> booking). No slice ships untested.
3. **Verify ISC** (Ideal Success Criteria): Compare against written, measurable criteria defined BEFORE the cycle — e.g. "quote PDF generated in <10s from a 60s voice note, correct GST line, sends via email". Binary pass/fail per criterion.
4. **Iterate**: On failure, diagnose root cause with a Tier 1 model (not symptom-patching), fix, and re-enter at Test.

**Cycle rules:**
- Max 5 cycles per outcome. If ISC unmet after 5, STOP — the plan is wrong, not the code. Re-plan with Fable 5 or kill the bet (2.5% rule: killing fast is winning).
- Each cycle logs: cycle #, what changed, test result, ISC pass/fail, tokens/cost spent.
- Kill triggers: projected build >30 days, spend approaching A$5K, or ISC needs redefining twice.
- BugBot reviews every PR between Build and Test.

---

## 6. `.cursorrules` Template

```
# .cursorrules — AU micro-SaaS MVP (1-2 person firm)

## Project context
- Micro-SaaS MVP for an AU-based solo firm. Target build: 7-30 days. Keep it shippable, not perfect.
- Stack: Next.js (App Router) + TypeScript + Supabase (Sydney region) + Stripe + Tailwind, unless PLAN.md says otherwise.
- Read PLAN.md before any multi-file change. If a change contradicts PLAN.md, stop and flag it instead of improvising.

## Code style
- TypeScript strict mode. No `any` without an inline justification comment.
- Small, single-purpose functions. Prefer server components; client components only for interactivity.
- No new dependencies without asking — every dep must earn its place in a 7-30 day MVP.
- Environment variables documented in .env.example the moment they are introduced.

## Australian requirements
- Currency: AUD, format A$X,XXX.XX. All prices GST-inclusive unless labelled "ex GST"; show GST as a separate line on invoices/quotes.
- Dates: DD/MM/YYYY. Timezone: Australia/Sydney default, configurable per account.
- Spelling: Australian English (organise, colour, licence/license distinction).
- Legal footer copy must reference Australian Consumer Law where refunds/guarantees are mentioned.

## Privacy & compliance (hard rules)
- No PII in logs, error messages, analytics events, or LLM prompts. Redact names, emails, phone numbers before any model call.
- Data stored in AU-region infrastructure only. No PII to third parties without an explicit, documented purpose.
- Any generated compliance/legal-adjacent content MUST carry: "General information only, not legal/financial advice."
- Collect the minimum data needed. Every new stored field needs a one-line justification comment in the schema.

## Testing
- Every feature slice ships with: (1) unit tests for logic, (2) one happy-path integration test, (3) explicit error-path handling.
- Money math is tested to the cent, including GST rounding.
- Never mark a task complete without running the tests and pasting the result.

## Workflow
- One feature per branch. Conventional commits (feat:, fix:, chore:).
- Before writing code for a task, restate the acceptance criteria in one sentence.
- If a fix attempt fails twice, stop and explain the root-cause hypothesis before trying again.
- Prefer editing existing files over creating new ones. No dead code, no TODO-littered stubs.
```

---

## 7. Cursor Pro Power User Tips

1. **One frontier planning session per MVP, then downshift.** Spend your first hour with Fable 5 in Max Mode producing `PLAN.md` (schema, routes, ISC, risks). Every subsequent session references that file with Tier 2/3 models — this single habit is the biggest cost and quality lever on a A$20/mo plan.
2. **Cmd+K is your default, chat is the exception.** For any change you can point at (rename, fix, tweak, extend a function), select and Cmd+K. Reserve chat/Composer for genuinely multi-file work. This is where the ~70% token saving actually accrues day-to-day.
3. **Make BugBot your second developer.** As a 1-person shop you have no reviewer — run BugBot on every PR before merging, and feed its findings back as an explicit fix list. It catches the "works on my machine" class of bugs that kill solo-built MVPs post-launch.
4. **Reuse a portfolio starter repo.** With 50+ bets, clone a template containing your `.cursorrules`, auth, Stripe billing, GST-aware invoice module, and test harness. Each MVP then starts at day 3, not day 0 — the compounding advantage across the portfolio dwarfs any single optimisation.
5. **Keep an evals folder for agent products.** For receptionist/agent bets (TradieDesk, TenderScout), store 20-30 real transcripts/inputs with expected outcomes and re-run them after every prompt or model change. It turns "seems better" into a pass/fail gate your 5-cycle loop can actually verify.
