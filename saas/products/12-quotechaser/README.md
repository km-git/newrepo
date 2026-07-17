# QuoteChaser (Rank #12)

Staged quote follow-ups for SMBs sending 20+ quotes per month.

```bash
npm install
npm run dev      # http://localhost:3011
npm test
npm run build
```

## Features

- 6 demo quotes from email/Xero sources
- Stale quote detection (3+ days, no reply)
- 3-stage follow-up cadence (day 3, 7, 14) with gentle → firm tone
- Draft → edit → approve → mock email send workflow
- 13 unit tests
