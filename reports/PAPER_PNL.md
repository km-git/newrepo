# Paper Execution P&L

**Run:** 2026-09-11T22:11:39.583730+00:00  
**Equity:** $50,000.00 → $49,992.54  
**Realized P&L:** $-7.46  
**Fees:** $2.99 @ 0.26%  
**Max positions:** 3  

## Summary

| Metric | Value |
|--------|-------|
| Executable candidates | 3 |
| Simulated (cap) | 2 |
| Blocked | 1 |
| Wins | 1 |
| Losses | 1 |
| No fill | 0 |

## Simulated Trades

| Symbol | TF | Tier | Status | Legs | P&L $ | Fees $ | Avg entry |
|--------|-----|------|--------|------|-------|--------|-----------|
| ZEC/USDT | 15m | probe | closed_sl | 4/4 | $1.10 | $1.87 | 1171.45226286 |
| RAY/USDT | 15m | probe | closed_sl | 4/4 | $-8.56 | $1.12 | 1.65653889 |

## Blocked (portfolio / gates)

| Symbol | TF | Reasons |
|--------|-----|---------|
| DOGE/USDT | 1d | tf_blocked=1d |

> OHLC limit fills · fees on entry+exit · SL before TP on same bar
> Source: `engine/paper_simulator.py`
