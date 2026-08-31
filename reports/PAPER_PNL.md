# Paper Execution P&L

**Run:** 2026-08-31T12:50:54.547214+00:00  
**Equity:** $50,000.00 → $50,000.00  
**Realized P&L:** $0.00  
**Fees:** $0.00 @ 0.26%  
**Max positions:** 3  

## Summary

| Metric | Value |
|--------|-------|
| Executable candidates | 11 |
| Simulated (cap) | 0 |
| Blocked | 11 |
| Wins | 0 |
| Losses | 0 |
| No fill | 0 |

## Simulated Trades

| Symbol | TF | Tier | Status | Legs | P&L $ | Fees $ | Avg entry |
|--------|-----|------|--------|------|-------|--------|-----------|

## Blocked (portfolio / gates)

| Symbol | TF | Reasons |
|--------|-----|---------|
| SOL/USDT | 15m | direction_blocked_LONG |
| BTC/USDT | 15m | direction_blocked_LONG |
| BTC/USDT | 1h | direction_blocked_LONG |
| BTC/USDT | 1w | direction_blocked_LONG |
| BTC/USDT | 12h | tf_blocked=12h |
| ZEC/USDT | 1w | direction_blocked_LONG |
| LIT/USDT | 1w | direction_blocked_LONG |
| XRP/USDT | 15m | direction_blocked_LONG |
| WLD/USDT | 15m | not_in_kill_zone |
| WLD/USDT | 1h | not_in_kill_zone |
| WLD/USDT | 1w | not_in_kill_zone |

> OHLC limit fills · fees on entry+exit · SL before TP on same bar
> Source: `engine/paper_simulator.py`
