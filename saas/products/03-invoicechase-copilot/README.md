# InvoiceChase Copilot (Rank #3)

Escalating invoice payment reminders for Xero/MYOB SMBs.

```bash
npm install
npm run dev      # http://localhost:3002
npm test
npm run build
```

## Features

- Mock aged-receivables dashboard (3 demo invoices)
- Escalation ladder: friendly (7d) → firm (21d) → final (35d)
- Approval queue before any reminder is sent
- Reply classifier: paid / dispute / promise-to-pay / opt-out
- 12 unit tests

## Compliance

**Payment reminders only** — not debt collection. Owner approves every outbound message.

## Env (optional live Xero)

```
XERO_CLIENT_ID=
XERO_CLIENT_SECRET=
XERO_REDIRECT_URI=
```

Without credentials, runs in mock mode with demo data.
