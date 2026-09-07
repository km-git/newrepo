# SaaS License & Spend — northwind

Draft reclaim pack for human review. As of 2026-09-07. Currency AUD. Do not auto-revoke.

**Reclaim (monthly): A$281.00** (A$3372.00/year) across 9 unused of 46 assigned seats.

## Bought vs used

| SKU | Bought | Used |
|---|---:|---:|
| m365-e5 | 20 | 16 |
| slack-business-plus | 12 | 9 |
| slack-guest | 3 | 3 |
| github-team | 10 | 8 |
| github-outside | 1 | 1 |


## Vendor reclaim

| Vendor | Unused seats | AUD / month |
|---|---:|---:|
| microsoft365 | 4 | 228.00 |
| slack | 3 | 45.00 |
| github | 2 | 8.00 |


## Department reclaim

| Department | Unused seats | AUD / month |
|---|---:|---:|
| finance | 2 | 114.00 |
| sales | 2 | 72.00 |
| hr | 1 | 57.00 |
| ops | 2 | 19.00 |
| marketing | 1 | 15.00 |
| eng | 1 | 4.00 |


## Idle buckets

| Bucket | Seats |
|---|---:|
| 0-29 | 33 |
| 30-59 | 2 |
| 60-89 | 2 |
| 90+ | 9 |
| unknown | 0 |


## Unused seats (hashed ids)

| User id | SKU | Idle days | Monthly AUD |
|---|---|---:|---:|
| `nw-m01` | m365-e5 | 280 | 57.00 |
| `nw-m02` | m365-e5 | 235 | 57.00 |
| `nw-m03` | m365-e5 | 218 | 57.00 |
| `nw-m04` | m365-e5 | 176 | 57.00 |
| `NWS01` | slack-business-plus | 230 | 15.00 |
| `NWS02` | slack-business-plus | 209 | 15.00 |
| `NWS03` | slack-business-plus | 190 | 15.00 |
| `nw-gh01` | github-team | 242 | 4.00 |
| `nw-gh02` | github-team | 199 | 4.00 |


## Renewals (60 days)

- github — 2026-09-27 — A$480.0 (draft nudge)
- microsoft365 — 2026-10-22 — A$13680.0 (draft nudge)


## Shadow apps

- Microsoft 365 (expense-csv)
- Slack (expense-csv)
- GitHub (expense-csv)
- Figma (expense-csv) — not in pricebook; possible shadow SaaS
- Loom (expense-csv) — not in pricebook; possible shadow SaaS
- Microsoft 365 (sso-catalog)
- Slack (sso-catalog)
- GitHub (sso-catalog)
- Figma (sso-catalog) — unapproved SSO app
- Loom (sso-catalog) — unapproved SSO app
- Miro (sso-catalog) — unapproved SSO app
- spf.protection.outlook.com (spf-include) — DNS heuristic only
- _spf.google.com (spf-include) — DNS heuristic only
- amazonses.com (spf-include) — DNS heuristic only
- mail.figma.com (spf-include) — DNS heuristic only


## Draft QBR talk-track

- Draft QBR talk-track for northwind as of 2026-09-07: 9 unused seats across github, microsoft365, slack = A$281.00/month (A$3372.00/year at operator list price).
- This is a spend report for human review. Do not auto-revoke seats.
- Highest-cost unused seat: m365-e5 (microsoft365) at A$57.00/month, idle 280 days (hashed id nw-m01).
- Renewals inside the 60-day window: github 2026-09-27, microsoft365 2026-10-22.
- Possible shadow SaaS (not in pricebook): Figma, Loom, Figma, Loom, Miro, spf.protection.outlook.com, _spf.google.com, amazonses.com.
- Action: walk the draft reclaim appendix with the tenant owner; dual-gate reclaim records intent only.


## Honest gaps

- Graph last-signin lags; idle is unused, not never.
- Slack guests are unbilled; conversations.history is never called.
- GitHub last-active uses audit-log events when present; outside collaborators are unbilled.
- Pricebook is operator-edited AUD list prices, not a crawler.
- Shadow scan is SSO catalog + SPF includes + expense CSV, not a CASB.
- Draft reclaim pack only. Dual-gate reclaim records intent; no vendor mutate APIs.


Watermark SHA-256: `242f7a35dd1589ea4d6d577bad0afd9469e46f354839c16442cfd21341018cc5`
