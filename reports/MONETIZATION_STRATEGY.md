# Monetization Strategy — Signal Licensing & Royalty Desk

Generated: **2026-09-05T00:55:08.078616+00:00**

> Bet-mode module. Turns EW + harmonic setups into a tiered signal service 
> with license watermarking and R-based royalty accounting.

## Inputs

- Signals loaded: **0**
- Resolved outcomes: **0**
- Subscribers: `{'free': 25, 'pro': 5, 'enterprise': 1}`
- Billing months: **1**

## Per-tier revenue

| Tier | Subs | Sub revenue | Wins | Losses | Decided WR | Σ R | +R | Royalty (R) |
|------|------|-------------|------|--------|------------|-----|----|-------------|
| free | 25 | A$0.00 | 0 | 0 | — | 0.00 | 0.00 | 0.0000 |
| pro | 5 | A$245.00 | 0 | 0 | — | 0.00 | 0.00 | 0.0000 |
| enterprise | 1 | A$249.00 | 0 | 0 | — | 0.00 | 0.00 | 0.0000 |

## Totals

- Subscribers: **31**
- Subscription revenue: **A$494.00**
- Royalty revenue (R): **0.0000**
- Total revenue (subs + royalty proxy): **A$494.00**

## Licensed signals (sample per tier)

### free — 0 signals after policy filter

- (no signals passed the tier policy filter)

### pro — 0 signals after policy filter

- (no signals passed the tier policy filter)

### enterprise — 0 signals after policy filter

- (no signals passed the tier policy filter)

## Notes

- Watermarks are SHA-256 over the signal identity subset (symbol, tf, 
  direction, WAE, SL, TPs, tiers). Any edit invalidates the hash.
- Free tier redacts entry / SL / TP; Pro exposes full signal; Enterprise 
  additionally exposes paper-fill trace and custom risk profile.
- Royalty is percent-of-positive-R on resolved outcomes (see engine/monetize.py).
- Source data: `output/v6_scanner/best_trades_latest.json`, 
  `output/autodream/tracked_setups.json` (closed list).
