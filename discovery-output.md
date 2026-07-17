# Cursor v4 Prompt Execution Output

## 1) 50+ ranked business ideas table

| # | Name | Category | Target | Problem | Solution | Architect Model | Workhorse Models | Cursor Workflow | Stack | Build Days | Setup A$ | Pricing | Y1 Mid Rev A$ | Success % | First Customer | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Tradie Quote Copilot | Tradie/NDIS | Electricians/plumbers | Slow quote turnaround | AI drafts itemized quotes from photos + voice notes | Opus 4.8 | Sonnet 5, Haiku 4.5, Luna | Plan in Opus, scaffold with Composer, refine with Cmd+K | Next.js, Supabase, OCR API | 14 | 1200 | A$79/mo | 60000 | 46% | Local sparkie | Photo quality variance |
| 2 | NDIS Progress Note AI | Tradie/NDIS | NDIS support workers | Notes are late and inconsistent | Speech-to-note + compliance template autofill | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus schema, Sonnet flows, Haiku polish | Next.js, Postgres, Whisper API | 18 | 1500 | A$99/mo | 80000 | 44% | Small NDIS provider | Compliance drift |
| 3 | Job Card to Invoice | Service Platforms | Field service SMBs | Double entry between job and invoice | Convert job cards to Xero-ready invoices | GPT-5.6 Sol | Sonnet 5, Luna | Sol UX, Composer scaffold, Haiku fixes | React, Node, Xero API | 12 | 900 | A$69/mo | 50000 | 42% | Plumbing shop | API changes |
| 4 | Local SEO Brief Generator | AI Content+SEO | Agencies | Slow brief writing | Auto-create suburb pages with intent clusters | Fable 5 | Sonnet 5, Haiku 4.5 | Fable strategy, Sonnet implementation | Next.js, OpenAI, SERP API | 10 | 700 | A$49/mo | 45000 | 48% | Local SEO freelancer | Search updates |
| 5 | Google Reviews Responder AU | AI Receptionist | Multi-location SMB | Review backlog hurts trust | AI drafts brand-safe responses with tone controls | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus guardrails, Sonnet app, Haiku tuning | Next.js, Firebase, GMB API | 9 | 600 | A$39/mo | 35000 | 52% | Dental clinic | Tone mistakes |
| 6 | Intake Form Builder AI | AI Workflow | Clinics/tradies | Long setup for forms | Prompt-to-form builder with validation rules | GPT-5.6 Sol | Sonnet 5, Luna | Sol form architecture, Sonnet backend | React, Zod, Supabase | 11 | 800 | A$59/mo | 40000 | 47% | Physio clinic | Edge-case validation |
| 7 | Tender Opportunity Scanner | Lead Gen | Construction SMB | Missed tender deadlines | Crawl portals, summarize fit, notify daily | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus extraction design, Sonnet worker | Python, FastAPI, Postgres | 16 | 1400 | A$129/mo | 70000 | 39% | Builder estimator | Source blocking |
| 8 | AI Call Summary to CRM | AI Workflow | Small sales teams | Lost call insights | Upload audio, get action items synced to CRM | GPT-5.6 Sol | Sonnet 5, Luna | Sol UX flow, Sonnet integrations | Node, HubSpot API, S3 | 13 | 1000 | A$89/mo | 65000 | 45% | B2B agency | Transcription errors |
| 9 | Churn Risk Mini-CDP | Analytics | Subscription SMB | No early churn signal | Basic event scoring + weekly churn list | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus model design, Sonnet ETL | Next.js, dbt-lite, Postgres | 20 | 1800 | A$149/mo | 90000 | 36% | SaaS founder | Sparse data |
| 10 | Complaint Triage Assistant | AI Compliance | E-commerce SMB | Slow complaint handling | Auto-categorize complaints + ACL playbook snippets | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus policy map, Sonnet app | Next.js, vector DB, queue | 15 | 1300 | A$99/mo | 60000 | 41% | Shopify store owner | Legal misread |
| 11 | Menu Cost Drift Monitor | Analytics | Cafes | Margin erosion unnoticed | Ingest supplier prices and flag menu risk | GPT-5.6 Sol | Sonnet 5, Luna | Sol dashboard, Sonnet ingestion | React, Python, Postgres | 12 | 1000 | A$79/mo | 50000 | 43% | Cafe operator | Bad supplier feeds |
| 12 | AI FAQ Widget Verticalized | Vertical AI Agents | Niche service sites | Generic chatbots underperform | Vertical-trained FAQ + lead capture handoff | Fable 5 | Sonnet 5, Haiku 4.5 | Fable niche design, Sonnet build | Next.js, RAG, Redis | 9 | 700 | A$59/mo | 55000 | 50% | Migration agent | Hallucinations |
| 13 | Property Maintenance Planner | Service Platforms | Property managers | Reactive maintenance costs more | Predictive task planner from ticket history | Opus 4.8 | Sonnet 5, Luna | Opus schema, Sonnet scheduling | Node, Postgres, cron workers | 17 | 1600 | A$139/mo | 85000 | 38% | Strata manager | Limited history |
| 14 | Subcontractor Compliance Vault | AI Compliance | Builders | Cert expiry causes risk | Track certs, expiry alerts, evidence packs | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus policy logic, Sonnet UI | Next.js, Supabase, file store | 14 | 1200 | A$89/mo | 70000 | 46% | Mid-size builder | Upload friction |
| 15 | AI Proposal Writer for MSPs | AI Tools SMB | IT MSPs | Proposals take too long | Turn discovery notes into proposal drafts | GPT-5.6 Sol | Sonnet 5, Luna | Sol doc flow, Sonnet editor | Next.js, TipTap, OpenAI | 10 | 900 | A$69/mo | 60000 | 49% | Small MSP | Generic outputs |
| 16 | Appointment No-Show Predictor | Analytics | Clinics/salons | No-shows cut revenue | Predict no-show risk and automate reminders | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus scoring, Sonnet reminders | Node, Twilio, Postgres | 13 | 1100 | A$79/mo | 55000 | 44% | Dental practice | False positives |
| 17 | AI Local Landing Page Pack | AI Localisation | Multi-suburb SMB | Hard to localize content | Generate suburb variants with offer controls | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol IA, Sonnet generation | Next.js, CMS, maps API | 8 | 500 | A$39/mo | 30000 | 51% | Trade marketing agency | Duplicate content |
| 18 | Job Safety Brief Generator | AI Compliance | Construction teams | Toolbox talks are repetitive | Auto-generate site-specific safety briefs | Opus 4.8 | Sonnet 5, Luna | Opus compliance framing, Sonnet app | React, PDF gen, Supabase | 11 | 900 | A$59/mo | 45000 | 47% | Site supervisor | Liability concerns |
| 19 | AI Inbox Prioritizer | AI Workflow | SMB founders | Important email gets buried | Score inbox by urgency and revenue impact | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol ranking UX, Sonnet backend | Node, Gmail API, Redis | 9 | 800 | A$29/mo | 35000 | 53% | Solo founder | API quota limits |
| 20 | Renewal Reminder Engine | Service Platforms | Insurance/accounting brokers | Renewals missed | Automated renewal timeline and nudges | Opus 4.8 | Sonnet 5, Luna | Opus workflow map, Sonnet jobs | Next.js, Postgres, SMS API | 12 | 950 | A$69/mo | 50000 | 48% | Local broker | Data sync failures |
| 21 | AI Brief-to-Ad Variants | AI Content+SEO | Local agencies | Ad iteration is slow | Generate compliant ad sets from one brief | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol creative controls, Sonnet build | React, Meta API, OpenAI | 10 | 850 | A$79/mo | 55000 | 45% | PPC freelancer | Platform policy shifts |
| 22 | Tradie Dispatch Optimizer | AI Workflow | Trade businesses | Inefficient daily routes | Suggest route + skill match by urgency | Opus 4.8 | Sonnet 5, Luna | Opus optimization model, Sonnet app | Next.js, maps API, Postgres | 19 | 1800 | A$149/mo | 95000 | 37% | HVAC business | Travel-time errors |
| 23 | AI Discovery Call Coach | AI Tools SMB | Sales teams | Calls lack structure | Live checklist + post-call scorecard | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol realtime UX, Sonnet event pipeline | React, WebRTC, Node | 21 | 2000 | A$129/mo | 85000 | 35% | Sales consultancy | Latency |
| 24 | Policy-to-Checklist Converter | AI Compliance | SMB operators | Policies are unreadable | Convert policy docs into actionable checklists | Opus 4.8 | Sonnet 5, Luna | Opus policy parser, Sonnet UI | Next.js, vector DB, parser | 14 | 1200 | A$89/mo | 65000 | 42% | HR consultant | Ambiguous policy text |
| 25 | AI Quoting for Cleaners | Vertical AI Agents | Cleaning companies | Manual site quote bottleneck | Estimate quote from room photos and notes | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol estimator UX, Sonnet backend | React, CV API, Postgres | 16 | 1600 | A$99/mo | 70000 | 40% | Commercial cleaner | CV misestimation |
| 26 | Voice Receptionist Lite | AI Receptionist | Clinics/tradies | Calls missed after-hours | AI call answering, booking, escalation | Fable 5 | Sonnet 5, Haiku 4.5 | Fable agent logic, Sonnet telephony | Twilio, Node, calendar API | 22 | 2000 | A$199/mo | 120000 | 33% | Physio clinic | Handoff failures |
| 27 | Onboarding Document Chaser | AI Workflow | Professional services | Clients delay onboarding docs | Automatic checklist chase with reminders | Opus 4.8 | Sonnet 5, Luna | Opus workflow, Sonnet automation | Next.js, email API, db | 8 | 600 | A$49/mo | 40000 | 52% | Bookkeeping firm | Spam filtering |
| 28 | Suburb Offer Heatmap | Analytics | Local franchises | No clarity on suburb demand | Heatmap from lead + conversion by suburb | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol map UX, Sonnet data pipeline | React, maps, Postgres | 11 | 900 | A$69/mo | 48000 | 46% | Home services franchise | Data sparsity |
| 29 | AI Job Ad Rewriter | AI Personalisation | Recruiters | Low-quality applications | Personalize ads by role, level, location | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol personalization model, Sonnet app | Next.js, ATS API, OpenAI | 9 | 700 | A$59/mo | 45000 | 49% | Boutique recruiter | Bias risk |
| 30 | Evidence Pack Generator | AI Compliance | NDIS providers | Audit prep is manual | Compile documents into audit-ready packs | Opus 4.8 | Sonnet 5, Luna | Opus compliance schema, Sonnet exporter | Next.js, file store, PDF | 15 | 1400 | A$109/mo | 80000 | 39% | NDIS coordinator | Missing documents |
| 31 | AI Upsell Prompt Engine | Lead Gen | Service sales reps | Missed upsell moments | Suggest contextual upsells from job data | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol scoring UX, Sonnet CRM sync | Node, CRM API, Redis | 12 | 1000 | A$79/mo | 60000 | 43% | Managed service team | Over-prompting |
| 32 | Meeting Follow-up Drafter | AI Tools SMB | Consultants | Follow-ups inconsistent | Draft recap, tasks, and next steps fast | GPT-5.6 Sol | Sonnet 5, Luna | Sol template system, Sonnet app | Next.js, calendar API, LLM | 7 | 400 | A$29/mo | 28000 | 56% | Solo consultant | Generic tone |
| 33 | Roster Gap Predictor | Analytics | Care/service ops | Last-minute roster gaps | Predict shifts at risk and propose backups | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus forecasting, Sonnet notifications | Python, Postgres, SMS | 20 | 1900 | A$149/mo | 90000 | 34% | Home care provider | Data quality |
| 34 | AI Case Note Quality Checker | AI Compliance | NDIS teams | Notes fail quality checks | Score notes against internal standards | Opus 4.8 | Sonnet 5, Luna | Opus rubric engine, Sonnet UI | React, Node, vector DB | 13 | 1100 | A$89/mo | 65000 | 42% | Support coordinator | Over-strict scoring |
| 35 | Subcontractor Marketplace Lite | Service Platforms | Builders/tradies | Hard to find vetted subcontractors | Match tasks to verified local subcontractors | Fable 5 | Sonnet 5, Haiku 4.5 | Fable marketplace design, Sonnet MVP | Next.js, Stripe Connect, Postgres | 27 | 2000 | A$149/mo + fee | 110000 | 31% | Residential builder | Liquidity chicken-egg |
| 36 | Lead Form Quality Filter | Lead Gen | Agencies | Low intent leads waste time | Score leads and auto-route by intent | GPT-5.6 Sol | Sonnet 5, Luna | Sol scoring controls, Sonnet webhook | Node, webhook, Redis | 8 | 500 | A$39/mo | 32000 | 54% | Performance agency | Wrong thresholds |
| 37 | AI FAQ from PDF Policy | AI Compliance | Regulated-light SMB | Policy PDFs not searchable | Build Q&A bot with citation snippets | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus RAG strategy, Sonnet app | Next.js, embeddings, pgvector | 12 | 950 | A$69/mo | 50000 | 47% | HR outsource firm | Citation mismatch |
| 38 | Estimate-to-Scope Converter | AI Workflow | Agencies/freelancers | Scope creep from vague estimates | Convert estimate into signed task scope | GPT-5.6 Sol | Sonnet 5, Luna | Sol workflow UX, Sonnet doc engine | React, e-sign API, db | 10 | 800 | A$59/mo | 42000 | 49% | Web agency | Legal wording |
| 39 | AI Personalised Onboarding Paths | AI Personalisation | B2B SaaS | Onboarding drop-off | Dynamic onboarding checklists by persona | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus decision graph, Sonnet app | Next.js, feature flags, db | 18 | 1700 | A$129/mo | 85000 | 36% | New SaaS startup | Over-complex rules |
| 40 | Cashflow Alert Copilot | Analytics | SMB owners | Cash crunch surprises | Predict shortfalls and suggest actions | Opus 4.8 | Sonnet 5, Luna | Opus forecasting, Sonnet dashboard | Node, bank feed API, Postgres | 16 | 1500 | A$119/mo | 78000 | 38% | Trade business owner | Bank feed gaps |
| 41 | AI Content Repurposer AU | AI Content+SEO | Coaches/agencies | Content creation is expensive | Turn one video into blog, email, socials | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol pipeline design, Sonnet generation | Next.js, media API, CMS | 9 | 700 | A$49/mo | 42000 | 50% | Business coach | Brand inconsistency |
| 42 | Compliance Deadline Radar | AI Compliance | SMB operations | Missed recurring obligations | Centralized deadline calendar + alerts | Opus 4.8 | Sonnet 5, Luna | Opus rule map, Sonnet reminders | Next.js, cron, notification API | 11 | 900 | A$79/mo | 55000 | 45% | Small manufacturer | Rule updates |
| 43 | AI Estimate Follow-up Bot | AI Receptionist | Tradies | Quotes not followed up | Automated follow-up SMS/email cadence | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol sequence UX, Sonnet scheduler | Node, SMS API, Postgres | 8 | 600 | A$49/mo | 38000 | 53% | Plumbing contractor | Spam complaints |
| 44 | Intake Risk Classifier | AI Workflow | Health/allied services | Risky intakes identified late | Classify intake risk and escalation path | Opus 4.8 | Sonnet 5, Luna | Opus triage logic, Sonnet forms | React, rules engine, db | 14 | 1200 | A$99/mo | 70000 | 41% | Allied health clinic | Misclassification |
| 45 | AI Quote Benchmarking | Analytics | Trade SMB | No sense of quote competitiveness | Compare quote ranges by suburb/job type | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol benchmark UI, Sonnet ingestion | Next.js, Postgres, charts | 13 | 1100 | A$89/mo | 62000 | 42% | Electrical contractor | Biased sample |
| 46 | SOP Builder from Screen Recordings | Dev Tools | Small ops teams | SOP writing is painful | Convert recordings into step-by-step SOP drafts | Fable 5 | Sonnet 5, Luna | Fable flow extraction, Sonnet editor | Next.js, speech API, markdown | 20 | 1900 | A$129/mo | 90000 | 34% | Ops manager | Transcription gaps |
| 47 | AI Localization QA | AI Localisation | SaaS teams | Local pages read awkwardly | Detect locale issues and rewrite in AU tone | GPT-5.6 Sol | Sonnet 5, Haiku 4.5 | Sol QA rubric, Sonnet app | Node, CMS API, LLM | 10 | 850 | A$69/mo | 50000 | 46% | SaaS marketer | Tone drift |
| 48 | Service Warranty Tracker | Service Platforms | Appliance/home service | Warranty obligations missed | Track warranty periods and service triggers | Opus 4.8 | Sonnet 5, Luna | Opus workflow, Sonnet reminder engine | Next.js, Postgres, email API | 9 | 750 | A$59/mo | 43000 | 49% | Appliance repair shop | Data entry burden |
| 49 | AI Proposal Risk Scanner | AI Compliance | Agencies/MSPs | Proposals hide risky clauses | Flag risky terms + plain-language notes | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus legal-lite parser, Sonnet UI | React, parser, vector DB | 12 | 1000 | A$79/mo | 58000 | 44% | Digital agency | False alarms |
| 50 | Referral Partner CRM Lite | Lead Gen | Local B2B services | Referral relationships unmanaged | Simple partner CRM + reward tracking | GPT-5.6 Sol | Sonnet 5, Luna | Sol UX, Sonnet backend | Next.js, Supabase, Stripe | 11 | 900 | A$69/mo | 52000 | 47% | Accountant | Manual adoption |
| 51 | AI Ticket Deflection for MSP | Vertical AI Agents | MSP helpdesks | Repetitive tickets overload team | Self-serve answer bot with escalation | Opus 4.8 | Sonnet 5, Haiku 4.5 | Opus RAG and escalation, Sonnet app | Node, embeddings, helpdesk API | 17 | 1500 | A$119/mo | 85000 | 38% | MSP owner | Incorrect deflection |
| 52 | Follow-up Probability Scorer | Analytics | Sales SMB | Reps chase wrong leads | Score likelihood of conversion next 7 days | Opus 4.8 | Sonnet 5, Luna | Opus model, Sonnet scoring service | Python, Postgres, dashboard | 15 | 1300 | A$99/mo | 72000 | 40% | B2B sales team | Label scarcity |

## 2) Top 10 picks (with one-line build plan + starting model)

1. Tradie Quote Copilot - Start with `Opus 4.8`: design quote schema, then scaffold photo upload + quote editor + export in Composer.
2. NDIS Progress Note AI - Start with `Opus 4.8`: define compliant note rubric, then ship voice capture and structured note output.
3. Voice Receptionist Lite - Start with `Fable 5`: architect telephony handoff/state machine, then implement Twilio + calendar booking.
4. Tender Opportunity Scanner - Start with `Opus 4.8`: define extraction + scoring logic, then implement crawler and morning digest.
5. Complaint Triage Assistant - Start with `Opus 4.8`: map ACL-friendly categories and response templates, then add workflow inbox.
6. AI Ticket Deflection for MSP - Start with `Opus 4.8`: design RAG plus escalation thresholds, then integrate with helpdesk APIs.
7. Dispatch Optimizer - Start with `Opus 4.8`: design routing constraints and priority scoring, then build planner UI.
8. Evidence Pack Generator - Start with `Opus 4.8`: define evidence model and export schema, then build guided pack builder.
9. Churn Risk Mini-CDP - Start with `Opus 4.8`: define event schema + risk formula, then ship weekly churn reports.
10. SOP Builder from Screen Recordings - Start with `Fable 5`: design transcript segmentation + SOP graph, then ship editor/export.

## 3) 4-tier routing pattern

- Tier 1 (Fable 5, Opus 4.8, GPT-5.6 Sol): use only for hardest architecture, security-sensitive design, or high-complexity UI/function-calling decisions.
- Tier 2 (Sonnet 5, Terra, Gemini Pro): use for most implementation work, refactors, code reviews, and day-to-day development.
- Tier 3 (Haiku 4.5, Luna, Flash, Grok, DeepSeek): use for fast iterative edits, boilerplate, and low-risk transformations.
- Tier 4 (Auto, Max, Composer, BugBot): use Auto when uncertain, Max for very large context, Composer for multi-file scaffolding, BugBot for focused debugging.

Rule of thumb: architect once with Tier 1, then ship mostly with Tier 2 and Tier 3.

## 4) Token-saving cheat sheet

- Use Cmd+K for 60-70% of line-level edits to keep chat context small.
- Keep one stable chat per feature to maximize prompt/cache reuse.
- Push heavy reasoning to 1-2 architect calls; do execution in cheaper calls.
- Use snippets for recurring boilerplate (auth, payments, schema, API handlers).
- Prefer diff-scoped prompts: "edit only this file/symbol" instead of broad rewrites.
- Use Composer for cross-file boilerplate, then Haiku/Luna for cleanup.
- Use Auto mode for uncertain tasks, then lock in cheaper model if stable.

## 5) Continuous testing loop (Build -> Test -> Verify -> Iterate)

1. Plan: define implementation success criteria in 1-2 concrete assertions.
2. Build: implement smallest vertical slice that can be run end-to-end.
3. Test: run focused automated checks + manual smoke path.
4. Verify: compare output to success criteria; list concrete pass/fail points.
5. Iterate: fix highest-impact failures first; cap at 3-5 loops before pivot/cut.
6. Finalize: document learnings, cost, and whether to continue investing.

## 6) `.cursorrules` template (drop-in)

```ini
# Project execution defaults
model_routing=tiered

# Tier policy
tier1_models=claude-fable-5-thinking-xhigh,claude-opus-4-8-thinking-high,gpt-5.6-sol-xhigh
tier2_models=claude-4.6-sonnet-high-thinking,gpt-5.5-high,gemini-3.1-pro
tier3_models=claude-haiku-4.5,gpt-5.6-luna,gemini-3.5-flash

# Rules
use_tier1_for=architecture,security,complex-refactor
use_tier2_for=default-dev,review,integration
use_tier3_for=boilerplate,small-edits,docstrings

# Workflow
default_cycle=plan->build->test->verify->iterate
max_iterations=5
prefer_cmdk=true
prefer_composer_for_multifile=true
```

## 7) Cursor Pro power-user tips (high impact)

- Keep one "architect thread" and one "execution thread" per feature to avoid context bloat.
- Ask for structured outputs first (schemas/checklists), then code generation second.
- Commit in short loops so model suggestions stay aligned to actual repo state.
- Pair Composer scaffolding with strict follow-up prompts: "remove dead code and tighten types."
- Track per-feature token spend and enforce a hard cap before adding scope.
