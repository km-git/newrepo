# MissedCall Rescue (Rank #1)

Instant SMS qualification when tradies miss inbound calls.

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev      # http://localhost:3000
npm test         # SMS state machine tests
npm run build
```

## Demo without Twilio

1. Open http://localhost:3000/dashboard
2. Click **Simulate missed call + SMS thread**
3. Lead card appears with job type, suburb, urgency

## Twilio setup

| Webhook | URL |
|---------|-----|
| Voice (status callback on no-answer) | `https://your-domain/api/webhooks/twilio/missed-call` |
| SMS inbound | `https://your-domain/api/webhooks/twilio/sms` |

## Flow

```
Missed call → auto SMS greeting → job type → suburb → urgency → notes → lead card
```

Emergency keywords (burst pipe, gas leak, no power) trigger owner SMS alert.

## Compliance

- STOP / UNSUBSCRIBE opt-out built in
- Store job metadata only — no health/financial PII
- Human reviews outbound scripts before production

## Stack

Next.js 15 · TypeScript · Tailwind · Twilio · (optional) Supabase · Stripe

Discovery spec: `discovery-output.md` Rank 1.
