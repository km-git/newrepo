# Inbox2Job (Rank #4)

Email enquiry → structured job card → ServiceM8/Tradify push.

```bash
npm install
npm run dev      # http://localhost:3003
npm test
npm run build
```

## Features

- Email extraction (name, phone, address, job type, urgency)
- Zod-validated job card schema
- Ambiguity flags for manual review
- Confirm-before-create workflow
- Mock ServiceM8 and Tradify push adapters
- 8 unit tests

## Env (optional live APIs)

```
SERVICEM8_API_KEY=
TRADIFY_API_KEY=
```
