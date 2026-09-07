# SaaS License & Spend — acme

Draft reclaim pack for human review. As of 2026-09-07. Currency AUD. Do not auto-revoke.

**Reclaim (monthly): A$127.00** (A$1524.00/year) across 5 unused of 26 assigned seats.

## Bought vs used

| SKU | Bought | Used |
|---|---:|---:|
| m365-e3 | 12 | 9 |
| slack-business-plus | 6 | 5 |
| slack-guest | 2 | 2 |
| github-team | 5 | 4 |
| github-outside | 1 | 1 |


## Vendor reclaim

| Vendor | Unused seats | AUD / month |
|---|---:|---:|
| microsoft365 | 3 | 108.00 |
| slack | 1 | 15.00 |
| github | 1 | 4.00 |


## Department reclaim

| Department | Unused seats | AUD / month |
|---|---:|---:|
| finance | 2 | 72.00 |
| hr | 1 | 36.00 |
| ops | 1 | 15.00 |
| eng | 1 | 4.00 |


## Idle buckets

| Bucket | Seats |
|---|---:|
| 0-29 | 20 |
| 30-59 | 1 |
| 60-89 | 0 |
| 90+ | 5 |
| unknown | 0 |


## Unused seats (hashed ids)

| User id | SKU | Idle days | Monthly AUD |
|---|---|---:|---:|
| `u-001` | m365-e3 | 249 | 36.00 |
| `u-002` | m365-e3 | 204 | 36.00 |
| `u-003` | m365-e3 | 190 | 36.00 |
| `S001` | slack-business-plus | 240 | 15.00 |
| `gh-001` | github-team | 245 | 4.00 |


## Renewals (60 days)

- microsoft365 — 2026-10-01 — A$5184.0 (draft nudge)


## Shadow apps

- Microsoft 365 (expense-csv)
- Slack (expense-csv)
- Notion (expense-csv) — not in pricebook; possible shadow SaaS
- Canva (expense-csv) — not in pricebook; possible shadow SaaS
- Microsoft 365 (sso-catalog)
- Slack (sso-catalog)
- Notion (sso-catalog) — unapproved SSO app
- Grammarly (sso-catalog) — unapproved SSO app
- _spf.google.com (spf-include) — DNS heuristic only
- spf.protection.outlook.com (spf-include) — DNS heuristic only
- mail.zendesk.com (spf-include) — DNS heuristic only


## Draft QBR talk-track

- Draft QBR talk-track for acme as of 2026-09-07: 5 unused seats across github, microsoft365, slack = A$127.00/month (A$1524.00/year at operator list price).
- This is a spend report for human review. Do not auto-revoke seats.
- Highest-cost unused seat: m365-e3 (microsoft365) at A$36.00/month, idle 249 days (hashed id u-001).
- Renewals inside the 60-day window: microsoft365 2026-10-01.
- Possible shadow SaaS (not in pricebook): Notion, Canva, Notion, Grammarly, _spf.google.com, spf.protection.outlook.com, mail.zendesk.com.
- Action: walk the draft reclaim appendix with the tenant owner; dual-gate reclaim records intent only.


## Honest gaps

- Graph last-signin lags; idle is unused, not never.
- Slack guests are unbilled; conversations.history is never called.
- GitHub last-active uses audit-log events when present; outside collaborators are unbilled.
- Pricebook is operator-edited AUD list prices, not a crawler.
- Shadow scan is SSO catalog + SPF includes + expense CSV, not a CASB.
- Draft reclaim pack only. Dual-gate reclaim records intent; no vendor mutate APIs.


Watermark SHA-256: `5026ae46e86f3077c843e6d7ba1a9ad6029f2995fd8ce202b13e5873762fbbdb`
