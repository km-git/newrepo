# Cursor v4 Frontier Discovery Output

> Generated from [v4 Frontier Prompt](https://r9cn7wx3yhf0z.space.minimax.io) — Turn 49 deep-research instructions.
>
> Operator context: AU 1–2 person firm · Cursor Pro A$20/mo · 7–30 day MVPs · A$0–2K setup · continuous testing max 5 cycles · 2.5% portfolio rule.

## 1. Ranked micro-SaaS / AI tool portfolio (56 businesses)

| # | Name | Category | Target | Problem | Solution | Architect Model | Workhorse Models | Cursor Workflow | Stack | Build Days | Setup A$ | Pricing | Y1 Mid Rev A$ | Success % | First Customer | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | QuoteSense AI | AI Tools SMB | AU tradies & SMBs | Quotes take hours; lost jobs from slow replies | AI quote builder from job photos + SMS follow-up | Opus 4.8 | Sonnet 5 + Haiku 4.5 | Fable plan → Composer scaffold → Haiku Cmd+K | Next.js + Supabase + Stripe + Twilio | 14 | 400 | A$49-149/mo | 36K | 42 | Facebook tradie groups + 1 free pilot | Adoption lag |
| 2 | InboxZero Pro | AI Tools SMB | Solo consultants | Email overload kills billable hours | AI triage + draft replies + CRM tags | Opus 4.8 | Haiku 4.5 + Luna | Opus schema → Sonnet API → Haiku polish | Next.js + Gmail API + Stripe | 10 | 200 | A$29-79/mo | 24K | 38 | LinkedIn cold DM to AU consultants | Gmail API limits |
| 3 | MeetingDigest AU | AI Tools SMB | Agencies & coaches | Meeting notes never become actions | Zoom/Meet → summary + tasks in Notion | GPT-5.6 Sol | Sonnet 5 + Luna | Sol UI → Composer → Haiku edits | Next.js + Recall.ai + Notion API | 12 | 300 | A$39-99/mo | 28K | 40 | Product Hunt + AU Slack communities | Meeting bot trust |
| 4 | PolicyBrief Bot | AI Tools SMB | SMB HR admins | Policies unread; compliance gaps | Upload policy PDF → staff Q&A chatbot | Opus 4.8 | Sonnet 5 + Haiku | Opus RAG design → Sonnet build | Next.js + pgvector + Stripe | 16 | 500 | A$79-199/mo | 32K | 35 | HR Facebook groups AU | Hallucination risk |
| 5 | SalonSlot AI | Micro-SaaS Vertical | Hair/beauty salons | No-shows + empty chairs | AI booking + SMS reminders + waitlist fill | GPT-5.6 Sol | Sonnet 5 + Haiku | Sol UI arch → Composer → Haiku | Next.js + Supabase + Twilio | 18 | 600 | A$59-149/mo | 42K | 45 | Local salon outreach VIC/NSW | Market saturation |
| 6 | VetFollow AI | Micro-SaaS Vertical | AU vet clinics | Missed recall vaccinations | AI recall SMS + portal for owners | Opus 4.8 | Sonnet 5 + Luna | Opus schema → Sonnet → Haiku | Next.js + Twilio + Stripe | 20 | 700 | A$99-249/mo | 48K | 40 | Vet association ads | Clinic IT friction |
| 7 | CafeWaste Watch | Micro-SaaS Vertical | Cafes & bakeries | Food waste eats margin | Photo inventory → waste forecast + order list | Opus 4.8 | Haiku 4.5 + Luna | Opus plan → Haiku heavy build | Next.js + vision API + Stripe | 14 | 350 | A$39-89/mo | 22K | 33 | Cafe owners IG + Facebook | Data entry habit |
| 8 | GymChurn Guard | Micro-SaaS Vertical | Boutique gyms | Members churn silently | Risk score + AI win-back messages | GPT-5.6 Sol | Sonnet 5 + Haiku | Sol agent design → Sonnet | Next.js + Mindbody API + Stripe | 21 | 800 | A$79-199/mo | 36K | 37 | Gym owner networks | API partner access |
| 9 | LeaseBot AU | Vertical AI Agents | Property managers | Lease questions flood inbox | RAG agent on lease + tenancy law FAQs | Fable 5 | Sonnet 5 + Haiku | Fable architect (legal) → Opus review → Sonnet | Next.js + pgvector + Stripe | 24 | 900 | A$149-399/mo | 55K | 34 | PM software partner referrals | Legal disclaimer risk |
| 10 | ClaimsPrep Agent | Vertical AI Agents | NDIS plan managers | Claims prep is manual & error-prone | Agent validates line items vs plan rules | Fable 5 | Opus 4.8 + Sonnet 5 | Fable schema → Opus tools → Sonnet | Next.js + Supabase + Xero | 28 | 1500 | A$299-799/mo | 72K | 36 | NDIS provider Facebook groups | Scheme rule changes |
| 11 | RecruitScreen Agent | Vertical AI Agents | AU recruiters | CV screening burns hours | Agent ranks CVs vs JD + bias checks | Opus 4.8 | Sonnet 5 + Haiku | Opus agent design → Sonnet | Next.js + S3 + Stripe | 16 | 500 | A$99-299/mo | 40K | 41 | Recruiter LinkedIn outreach | Fairness/compliance |
| 12 | SupportTier Agent | Vertical AI Agents | SaaS support teams | L1 tickets clog humans | Multi-tool agent: docs + refunds + escalate | GPT-5.6 Sol | Sonnet 5 + Luna | Sol function-calling → Composer | Next.js + Intercom API + Stripe | 18 | 600 | A$149-399/mo | 52K | 39 | IndieHackers + SaaS Slack | Wrong refunds |
| 13 | LocalRank Writer | AI Content+SEO | AU local SMBs | Can't afford SEO agencies | City+service page generator + GBP posts | Opus 4.8 | Haiku 4.5 + Luna | Opus SEO brief → Haiku volume | Next.js + OpenAI + Stripe | 10 | 250 | A$49-129/mo | 30K | 44 | Google Business Profile outreach | AI content penalties |
| 14 | ReviewReply Pro | AI Content+SEO | Multi-location retail | Review replies inconsistent | Brand-voice AI replies + escalate flags | GPT-5.6 Sol | Haiku 4.5 + Luna | Sol UI → Haiku templates | Next.js + Google APIs + Stripe | 12 | 300 | A$39-99/mo | 28K | 48 | Agency white-label partners | API rate limits |
| 15 | PodcastClip Farm | AI Content+SEO | Coaches & podcasters | Long audio unused | Auto clips + captions + LinkedIn packs | Sonnet 5 (arch light) | Haiku 4.5 + Luna | Composer scaffold → Haiku | Next.js + Whisper + Stripe | 14 | 400 | A$29-79/mo | 20K | 40 | Podcast host communities | Commodity pricing |
| 16 | SchemaBoost AU | AI Content+SEO | AU web agencies | Clients miss rich results | Site crawl → schema JSON-LD installer | Opus 4.8 | Sonnet 5 + Haiku | Opus schema rules → Sonnet | Next.js + Puppeteer + Stripe | 15 | 450 | A$79-199/mo | 34K | 38 | Agency partner program | CMS edge cases |
| 17 | PRRisk Lens | Dev Tools | Eng managers | Risky PRs merge unnoticed | AI risk score + test gap report on PRs | Opus 4.8 | Sonnet 5 + Haiku | Opus design → Sonnet GitHub App | Next.js + GitHub App + Stripe | 16 | 400 | A$49-199/mo | 36K | 42 | GitHub Marketplace | False positives |
| 18 | EnvDiff Guard | Dev Tools | DevOps solos | Prod/staging config drift | Diff env secrets/config + alert | Opus 4.8 | Haiku 4.5 + Luna | Opus plan → Haiku CLI polish | Go CLI + Next.js dashboard | 12 | 200 | A$29-99/mo | 18K | 40 | Dev Twitter/X + HN | Secret handling trust |
| 19 | APIMock Studio | Dev Tools | Frontend teams | Backend blocked FE velocity | OpenAPI → realistic mock + scenarios | GPT-5.6 Sol | Sonnet 5 + Luna | Sol UI → Composer → Haiku | Next.js + Prisma + Stripe | 14 | 350 | A$39-129/mo | 26K | 43 | Frontend Discord servers | OpenAPI quality |
| 20 | ChangelogGen | Dev Tools | SaaS founders | Release notes always late | PR titles → customer changelog + email | Sonnet 5 | Haiku 4.5 + Luna | Composer → Haiku volume | Next.js + GitHub + Resend | 8 | 150 | A$19-59/mo | 14K | 46 | IndieHackers launch | Low willingness to pay |
| 21 | ZapAudit AI | AI Workflow | Ops managers | Zapier sprawl; broken zaps | Map workflows + suggest consolidations | Opus 4.8 | Sonnet 5 + Haiku | Opus graph model → Sonnet | Next.js + Zapier API + Stripe | 18 | 500 | A$79-199/mo | 32K | 37 | No-code communities | API permissions |
| 22 | SOPify | AI Workflow | Growing SMBs | Knowledge in people's heads | Record screen/call → living SOP wiki | GPT-5.6 Sol | Sonnet 5 + Haiku | Sol multimodal → Sonnet | Next.js + Whisper + Notion | 16 | 450 | A$59-149/mo | 30K | 41 | SMB Facebook groups | Adoption of SOPs |
| 23 | HandOff Hub | AI Workflow | Agencies | Client handoffs drop balls | AI checklist + status from Slack/email | Opus 4.8 | Haiku 4.5 + Luna | Opus schema → Haiku UI | Next.js + Slack API + Stripe | 14 | 350 | A$49-129/mo | 26K | 39 | Agency owner masterminds | Slack noise |
| 24 | ApprovalFlow Lite | AI Workflow | Finance SMBs | Invoice approvals via email chaos | Lightweight approval chains + audit log | Opus 4.8 | Sonnet 5 + Luna | Opus state machine → Sonnet | Next.js + Supabase + Stripe | 15 | 400 | A$39-99/mo | 24K | 40 | Xero advisor partners | Incumbent accounting |
| 25 | WarmIntro Finder | Lead Gen | B2B freelancers | Cold outreach converts poorly | LinkedIn graph + mutual intro scripts | Opus 4.8 | Sonnet 5 + Haiku | Opus scoring → Sonnet | Next.js + LinkedIn API + Stripe | 16 | 500 | A$79-199/mo | 34K | 35 | Freelance Slack communities | LinkedIn ToS risk |
| 26 | LocalLead Radar | Lead Gen | Tradies & cleaners | Inconsistent lead flow | Scrape permit/ABN signals → daily leads | Opus 4.8 | Haiku 4.5 + Luna | Opus scrape ethics → Haiku | Next.js + Playwright + Stripe | 18 | 600 | A$99-249/mo | 45K | 38 | Tradie Facebook groups | Data source fragility |
| 27 | RFP Scout | Lead Gen | IT services firms | Miss gov/tender RFPs | Keyword watch + fit score + draft response | Fable 5 | Opus 4.8 + Sonnet 5 | Fable tender logic → Opus → Sonnet | Next.js + scrapers + Stripe | 22 | 800 | A$149-399/mo | 50K | 36 | IT services LinkedIn | Tender site changes |
| 28 | ReferralOS | Lead Gen | Dentists & physios | Referrals untracked | Referral portal + AI thank-you + analytics | GPT-5.6 Sol | Sonnet 5 + Haiku | Sol UI → Composer → Haiku | Next.js + Twilio + Stripe | 14 | 400 | A$59-149/mo | 28K | 42 | Allied health associations | Clinic IT barriers |
| 29 | StripePulse AU | Analytics | Indie SaaS | Don't know which plan churns why | Cohort + AI narrative on Stripe data | Opus 4.8 | Sonnet 5 + Luna | Opus metrics → Sonnet charts | Next.js + Stripe API | 12 | 300 | A$39-99/mo | 22K | 44 | IndieHackers + X | Baremetrics competition |
| 30 | AdWaste Finder | Analytics | SMB advertisers | Meta/Google ad spend leaks | AI finds wasted spend + creative tips | Opus 4.8 | Sonnet 5 + Haiku | Opus analysis → Sonnet | Next.js + Ads APIs + Stripe | 18 | 700 | A$99-299/mo | 40K | 37 | Agency white-label | API access approval |
| 31 | NPSAction | Analytics | CX managers | NPS collected, never acted | Route detractors + AI reply drafts | GPT-5.6 Sol | Haiku 4.5 + Luna | Sol workflows → Haiku | Next.js + Typeform + Stripe | 10 | 250 | A$49-129/mo | 20K | 43 | CX LinkedIn groups | Survey fatigue |
| 32 | Cashflow Story | Analytics | Tradie owners | Xero confusing; cash surprises | Weekly plain-English cash story SMS | Opus 4.8 | Sonnet 5 + Haiku | Opus finance rules → Sonnet | Next.js + Xero + Twilio | 16 | 500 | A$29-79/mo | 26K | 45 | Accountant partnerships | Xero partner rules |
| 33 | ExpertHours Marketplace | Service Platforms | AU specialists | Hard to sell leftover hours | Bookable micro-consult slots + AI matching | GPT-5.6 Sol | Sonnet 5 + Haiku | Sol marketplace UI → Composer | Next.js + Stripe Connect + Cal | 24 | 1000 | 15% take rate | 48K | 32 | Specialist LinkedIn | Two-sided cold start |
| 34 | WhiteLabel Chat Desk | Service Platforms | Digital agencies | Need branded chat for clients | Multi-tenant chat + billing per seat | Fable 5 | Opus 4.8 + Sonnet 5 | Fable multi-tenant → Opus → Composer | Next.js + Supabase + Stripe | 28 | 1200 | A$199-599/mo | 65K | 34 | Agency partner channel | Support burden |
| 35 | CompliancePack Hub | Service Platforms | AU SMBs | Policies/templates scattered | Pack marketplace + AI customiser | Opus 4.8 | Sonnet 5 + Luna | Opus content model → Sonnet | Next.js + Stripe + MDX | 14 | 350 | A$19-79/mo + packs | 24K | 40 | Accountant/HR partners | Template liability |
| 36 | SiteCare Desk | Service Platforms | WordPress agencies | Retainer updates chaotic | Client portal + AI change tickets | GPT-5.6 Sol | Haiku 4.5 + Luna | Sol portal UI → Haiku | Next.js + WP API + Stripe | 16 | 450 | A$49-149/mo | 30K | 41 | WP agency Facebook groups | Scope creep |
| 37 | TradieBot Pro | Tradie/NDIS | AU tradies | Miss calls = miss jobs | AI chatbot + SMS quote follow-up + CRM sync | Opus 4.8 | Sonnet 5 + Haiku | Opus ServiceM8 schema → Composer → Haiku | Next.js + Tidio/custom + ServiceM8 | 21 | 500 | A$149-399/mo | 60K | 48 | Tradie FB groups + 3 pilots | Slow adoption |
| 38 | TradieVoice Desk | Tradie/NDIS | Busy trade businesses | After-hours calls lost | White-label AI phone receptionist | GPT-5.6 Sol | Opus 4.8 + Sonnet 5 | Sol voice tools → Opus → Sonnet | Synthflow/Twilio + Next.js | 25 | 2000 | A$299-799/mo | 55K | 40 | Reseller to chatbot clients | Voice quality/cost |
| 39 | NDIS Intake Copilot | Tradie/NDIS | NDIS providers | Intake admin 10-20 hrs/wk | Intake chatbot + plan enquiry + referral routing | Fable 5 | Opus 4.8 + Sonnet 5 | Fable compliance arch → Opus → Sonnet | Next.js + RAG + Stripe | 28 | 1000 | A$499-1499/mo | 80K | 42 | NDIS provider networks | Privacy + accuracy |
| 40 | NDIS Notes Assist | Tradie/NDIS | Support workers | Progress notes late/incomplete | Voice → structured notes + standards hints | Opus 4.8 | Sonnet 5 + Haiku | Opus note schema → Sonnet | Next.js + Whisper + Stripe | 18 | 600 | A$79-199/mo | 38K | 44 | Provider office managers | Clinical risk |
| 41 | ClinicFront AI | AI Receptionist | Allied health clinics | Reception overloaded | Omnichannel receptionist: phone+web+SMS | GPT-5.6 Sol | Sonnet 5 + Haiku | Sol orchestration → Composer | Next.js + Twilio + Cal.com | 22 | 900 | A$199-499/mo | 52K | 41 | Allied health associations | Booking errors |
| 42 | LawFirm Desk AI | AI Receptionist | Small AU law firms | Conflict checks + intake messy | AI intake + conflict triage + calendar | Fable 5 | Opus 4.8 + Sonnet 5 | Fable legal intake → Opus → Sonnet | Next.js + Clio API + Stripe | 26 | 1200 | A$299-799/mo | 58K | 33 | Law society events | Professional risk |
| 43 | Restaurant Host AI | AI Receptionist | Restaurants | Phone bookings interrupt service | Voice/SMS booking + waitlist agent | GPT-5.6 Sol | Haiku 4.5 + Luna | Sol voice → Haiku polish | Twilio + Next.js + Stripe | 16 | 500 | A$99-249/mo | 34K | 39 | Hospitality FB groups | Accent/noise issues |
| 44 | StrataDesk AI | AI Receptionist | Strata managers | Owner calls about same issues | FAQ voice/chat + work-order create | Opus 4.8 | Sonnet 5 + Luna | Opus domain → Sonnet | Next.js + Twilio + Stripe | 18 | 600 | A$149-349/mo | 36K | 40 | Strata software partners | Angry owner edge cases |
| 45 | PrivacyAct Mapper | AI Compliance | AU SMBs | Privacy Act obligations unclear | Gap quiz → policy pack + evidence log | Opus 4.8 | Sonnet 5 + Haiku | Opus AU law map → Sonnet | Next.js + Stripe + MDX | 20 | 700 | A$99-299/mo | 40K | 38 | Accountant channel | Not legal advice risk |
| 46 | ACL Claim Shield | AI Compliance | D2C ecommerce | ACL refund disputes messy | Scripted responses + evidence checklist | Opus 4.8 | Haiku 4.5 + Luna | Opus ACL rules → Haiku | Next.js + Shopify + Stripe | 14 | 400 | A$49-149/mo | 28K | 40 | Shopify AU merchants | Edge-case liability |
| 47 | NDIS Standards Check | AI Compliance | NDIS providers | Practice Standards audits stressful | Self-audit chatbot + evidence folder | Fable 5 | Opus 4.8 + Sonnet 5 | Fable standards → Opus → Sonnet | Next.js + S3 + Stripe | 24 | 900 | A$199-499/mo | 48K | 37 | NDIS consultants | Standards updates |
| 48 | WHS Toolbox AI | AI Compliance | Trade employers | Toolbox talks skipped | Site-specific WHS briefs + quiz SMS | Opus 4.8 | Sonnet 5 + Haiku | Opus WHS content → Sonnet | Next.js + Twilio + Stripe | 15 | 450 | A$59-149/mo | 30K | 43 | Safety officer networks | Content accuracy |
| 49 | AUSpeak Localiser | AI Localisation | Global SaaS entering AU | US English/UX misfires AU market | AU spelling, currency, idioms, ABN flows | Opus 4.8 | Haiku 4.5 + Luna | Opus glossary → Haiku batch | Next.js + i18n + Stripe | 12 | 300 | A$79-199/mo | 22K | 36 | SaaS expansion Slack | Thin market |
| 50 | SuburbCopy AI | AI Localisation | Franchise marketers | National copy ignores suburbs | Generate suburb-aware landing variants | GPT-5.6 Sol | Haiku 4.5 + Luna | Sol templates → Haiku volume | Next.js + Maps data + Stripe | 14 | 400 | A$49-129/mo | 26K | 41 | Franchise marketing teams | Generic output |
| 51 | Multilingual Care Desk | AI Localisation | Aged care / NDIS | CALD families underserved | Intake chatbot EN/ZH/VI/AR | Opus 4.8 | Sonnet 5 + Haiku | Opus i18n RAG → Sonnet | Next.js + translation APIs | 20 | 800 | A$149-399/mo | 36K | 35 | Multicultural provider networks | Translation quality |
| 52 | TimezoneOnboard | AI Localisation | Remote AU teams | Global clients confused by AEST | Smart scheduling + local holiday packs | Sonnet 5 | Luna + Haiku | Composer → Luna boilerplate | Next.js + Cal + Stripe | 8 | 150 | A$19-49/mo | 12K | 42 | Remote work communities | Calendly competition |
| 53 | OfferFit Lite | AI Personalisation | D2C brands | Same offer to everyone | Segment + personalised offer emails | Opus 4.8 | Sonnet 5 + Haiku | Opus scoring → Sonnet | Next.js + Shopify + Klaviyo | 18 | 600 | A$99-249/mo | 38K | 39 | D2C Slack communities | Data volume needed |
| 54 | CoursePath AI | AI Personalisation | Online educators | One-size courses lose students | Adaptive path + nudge emails | GPT-5.6 Sol | Sonnet 5 + Luna | Sol learning UX → Sonnet | Next.js + Supabase + Stripe | 16 | 500 | A$59-149/mo | 28K | 40 | Course creator groups | Content tagging cost |
| 55 | JobSite Digest | AI Personalisation | Tradies | Irrelevant job leads waste time | Personalised lead digest by trade/suburb | Opus 4.8 | Haiku 4.5 + Luna | Opus ranking → Haiku | Next.js + scrapers + Stripe | 14 | 400 | A$39-99/mo | 32K | 44 | Tradie FB + TikTok ads | Lead quality variance |
| 56 | ClientTone Mirror | AI Personalisation | Agencies | Brand voice drifts across writers | Voice model per client + draft rewrite | Opus 4.8 | Sonnet 5 + Haiku | Opus style model → Sonnet | Next.js + embeddings + Stripe | 12 | 350 | A$49-129/mo | 24K | 43 | Agency ops managers | Overfitting voice |

## 2. Top 10 picks (1-line build plan + start model)

1. **#37 TradieBot Pro** — Ship Tidio/custom chat + ServiceM8 sync + Stripe in 21d; pilot 3 tradies with free month. Start: **Opus 4.8**.
2. **#39 NDIS Intake Copilot** — Fable-architect RAG intake + plan FAQ; Opus tool layer; Sonnet delivery; 1 provider pilot. Start: **Fable 5**.
3. **#38 TradieVoice Desk** — GPT-5.6 Sol voice tool design on Synthflow/Twilio; upsell from TradieBot users. Start: **GPT-5.6 Sol**.
4. **#26 LocalLead Radar** — Opus ethics/scrape plan; Haiku scrapers; daily SMS digests to tradies. Start: **Opus 4.8**.
5. **#10 ClaimsPrep Agent** — Fable claims-rules schema; Opus validators; Xero export; sell to plan managers. Start: **Fable 5**.
6. **#5 SalonSlot AI** — Sol booking UI; Composer Next+Supabase; Twilio waitlist fill. Start: **GPT-5.6 Sol**.
7. **#32 Cashflow Story** — Opus Xero cash rules; weekly SMS narrative; accountant channel. Start: **Opus 4.8**.
8. **#14 ReviewReply Pro** — Sol brand-voice UI; Haiku reply templates; Google reviews API. Start: **GPT-5.6 Sol**.
9. **#45 PrivacyAct Mapper** — Opus AU Privacy Act map; Sonnet quiz+policy packs; accountant affiliates. Start: **Opus 4.8**.
10. **#17 PRRisk Lens** — Opus GitHub App design; Sonnet risk model; Marketplace listing. Start: **Opus 4.8**.

## 3. 4-tier routing pattern

| Tier | Models | When | Share of work |
|---|---|---|---|
| **1 Frontier Architect** | Fable 5 · Opus 4.8 · GPT-5.6 Sol | Hardest multi-file/security/schema; UI+tool-calling architecture | 5–10 calls/month |
| **2 Balanced Heavy** | Sonnet 5 · Terra · Opus 4.5–4.7 · Gemini 3.1 Pro | Daily coding, review, long-context docs | ~20–30% (Sonnet = 90% of daily coding) |
| **3 Cheap Workhorse** | Haiku 4.5 · Luna · Flash · Grok 4.5 · DeepSeek | Cmd+K edits, docstrings, boilerplate | 60–70% |
| **4 Cursor Built-in** | Auto · Max · Composer 1 · BugBot | Routine pick / big context / multi-file / debug | As needed |

**Decision shortcuts**

1. Hardest architect / 1000+ LOC refactor / security → **Fable 5** (else Opus 4.8)
2. Standard schema / audit / complex logic → **Opus 4.8** (else GPT-5.6 Sol)
3. UI architecture / function calling / multi-agent → **GPT-5.6 Sol**
4. Daily coding / refactor / review → **Sonnet 5**
5. Long docs / multimodal / AU context → **Gemini 3.1 Pro**
6. Inline edit / docstring / simple fix → **Haiku 4.5** (else Luna)
7. Boilerplate / autocomplete → **Luna / Flash / Tab**
8. Multi-file scaffold → **Composer 1**
9. Unsure → **Auto mode**
10. Huge context refactor → **Max Mode**

NEVER Tier 1 for workhorse. NEVER Tier 3 for architect.

## 4. Token-saving cheat sheet

| Lever | Practice | Effect |
|---|---|---|
| Cmd+K heavy | ~70% of edits inline, not chat | No chat-context bloat |
| 4-tier routing | Cheapest adequate model | 70–90% vs always-frontier |
| Session cache | Keep one chat for related work | Free context reuse |
| `.cursorrules` | Project root instructions | Free system guidance |
| Snippets | Stripe/Prisma/auth boilerplate | −200+ tokens/use |
| Tab | Routine completions | Near-free |
| Composer batch | Multi-file in one call | Less re-prompting |
| BugBot | Debug path | ~3× faster, ~22% cheaper |
| Critical-only frontier | 1–2 Fable calls/MVP | Stay inside A$20 pool |

## 5. Continuous testing loop (max 5 cycles)

```
PLAN (Tier 1: Fable 5 or Opus 4.8)
  → ISC in 1–2 sentences · schema · file plan · deps
BUILD (Tier 2–3: Sonnet 5 + Haiku 4.5)
  → Composer scaffold · Sol/Sonnet UI · Haiku Cmd+K
TEST (mostly no AI)
  → unit + smoke · capture failure modes
VERIFY (Tier 2: Sonnet 5)
  → ISC met? YES → FINALIZE · NO → BUILD again
FINALIZE
  → document outcome · portfolio update · 7-day cut if failing
LOOP ≤ 5 cycles/MVP · Friday portfolio review
```

**ISC examples (top bets)**

- TradieBot Pro: *Pilot tradie receives quote request via chat and SMS follow-up within 60s; setup < 1 day.*
- NDIS Intake Copilot: *Provider staff completes intake via chat with plan-rule citations; zero PII in logs beyond retention policy.*
- LocalLead Radar: *Daily lead SMS with suburb+trade filter; ≥70% relevant leads in week-1 pilot.*

## 6. `.cursorrules` template

See project root `.cursorrules` (installed from this discovery run).

## 7. Cursor Pro power-user tips (high-impact)

1. **Budget frontier**: Cap Fable 5 / Opus 4.8 / Sol at 5–10 architect calls/month; Sonnet 5 for daily; Haiku for Cmd+K volume.
2. **Cmd+K is the token firewall**: Prefer inline edits for polish so chat stays short and cheap.
3. **One ISC sentence before build**: If you can't state the success check, don't open Composer yet.
4. **Composer for scaffolds, BugBot for breaks**: Don't burn frontier tokens on either.
5. **Friday cut rule**: Kill MVPs that miss ISC after ≤5 cycles within 7 days — protect the 50–55 bet portfolio.

---

## Appendix A — Portfolio math (operator targets)

| Metric | Target |
|---|---|
| Bets in this table | 56 |
| Build window | 7–30 days |
| Setup ceiling | A$0–2K (most ≤ A$1K) |
| Y1 mid revenue (sum of mid estimates, not additive) | Use Top 10 concentration |
| Expected winners (2.5% rule on 50–55) | ~1–2 scale winners |
| Y1 revenue goal | A$220K (1p) / A$330K (2p) |
| Blended success filter | Prefer ≥35% rows for first builds |

## Appendix B — Category coverage

| Category | Count |
|---|---:|
| AI Tools SMB | 4 |
| Micro-SaaS Vertical | 4 |
| Vertical AI Agents | 4 |
| AI Content+SEO | 4 |
| Dev Tools | 4 |
| AI Workflow | 4 |
| Lead Gen | 4 |
| Analytics | 4 |
| Service Platforms | 4 |
| Tradie/NDIS | 4 |
| AI Receptionist | 4 |
| AI Compliance | 4 |
| AI Localisation | 4 |
| AI Personalisation | 4 |
| **Total** | **56** |

## Appendix C — Next execution steps (from prompt §10.3)

1. ✅ Paste/run v4 prompt → this file (`discovery-output.md`)
2. ✅ Install `.cursorrules` in project root
3. Pick Top 3 from §2; write ISC; open Composer scaffold on Sonnet 5 / Opus plan
4. Haiku 4.5 via Cmd+K for most edits
5. Apply continuous testing loop (max 5 cycles)
6. Friday portfolio review + 7-day cut rule

