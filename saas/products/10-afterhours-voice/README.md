# AfterHours Voice Agent (Rank #10)

After-hours voice agent for emergency-capable trades with triage, callback booking, and SMS escalation.

```bash
npm install
npm run dev      # http://localhost:3009
npm test
npm run build
```

## Features

- Versioned call flow configuration (v1.0.0)
- Simulated-call test harness (no Twilio required)
- Emergency triage with business-defined keywords
- Callback slot booking for non-emergencies
- SMS escalation to on-call technician (mock)
- Auto recording purge after call completion
- 11 unit tests
