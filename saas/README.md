# Micro-SaaS Portfolio

Runnable MVPs for the 56 ranked ideas in [`discovery-output.md`](../discovery-output.md).

## Build order

Products are built **one by one** in global rank order. See [`BUILD_TRACKER.md`](BUILD_TRACKER.md) for status.

## Quick start (product #1)

```bash
cd saas/products/01-missed-call-rescue
cp .env.example .env.local
npm install
npm run dev          # http://localhost:3000
npm test             # state machine + webhook tests
```

## Shared code

`saas/shared/` — types and provider-agnostic LLM workhorse used across products.

## Model roles (from discovery)

- **Architect model** — design-time only (schemas, eval sets, edge cases)
- **Workhorse model** — runtime drafting behind a swappable adapter
- **Human approval** — required before outbound SMS, publishing, or money
