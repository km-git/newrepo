# Paper Execution P&L

**Run:** 2026-08-31T09:34:44.736289+00:00  
**Equity:** $50,000.00 → $50,000.00  
**Realized P&L:** $0.00  
**Fees:** $0.00 @ 0.26%  
**Max positions:** 3  

## Summary

| Metric | Value |
|--------|-------|
| Executable candidates | 28 |
| Simulated (cap) | 2 |
| Blocked | 26 |
| Wins | 0 |
| Losses | 0 |
| No fill | 0 |

## Simulated Trades

| Symbol | TF | Tier | Status | Legs | P&L $ | Fees $ | Avg entry |
|--------|-----|------|--------|------|-------|--------|-----------|
| WLD/USDT | 15m | — | error | — | — | — | no_ohlc |
| WLD/USDT | 1h | — | error | — | — | — | no_ohlc |

## Blocked (portfolio / gates)

| Symbol | TF | Reasons |
|--------|-----|---------|
| SOL/USDT | 15m | direction_blocked_LONG |
| ZEC/USDT | 15m | direction_blocked_LONG |
| TRUMP/USDT | 15m | direction_blocked_LONG |
| SOL/USDT | 1h | direction_blocked_LONG |
| ZEC/USDT | 1h | direction_blocked_LONG |
| TRUMP/USDT | 1h | direction_blocked_LONG |
| SOL/USDT | 1w | direction_blocked_LONG |
| ZEC/USDT | 1w | direction_blocked_LONG |
| TRUMP/USDT | 1w | direction_blocked_LONG |
| WLD/USDT | 1w | tf_disabled=1w |
| SOL/USDT | 12h | tf_blocked=12h |
| ZEC/USDT | 12h | tf_blocked=12h |
| TRUMP/USDT | 12h | tf_blocked=12h |
| WLD/USDT | 12h | tf_blocked=12h |
| BTC/USDT | 15m | direction_blocked_LONG |
| LINK/USDT | 15m | not_in_kill_zone |
| BTC/USDT | 1h | direction_blocked_LONG |
| XRP/USDT | 1h | direction_blocked_LONG |
| UNI/USDT | 1h | direction_blocked_LONG |
| OKB/USDT | 1h | direction_blocked_LONG |
| BTC/USDT | 1w | direction_blocked_LONG |
| ETH/USDT | 1w | direction_blocked_LONG |
| XRP/USDT | 1w | direction_blocked_LONG |
| OKB/USDT | 1w | direction_blocked_LONG |
| BTC/USDT | 12h | tf_blocked=12h |
| OKB/USDT | 12h | tf_blocked=12h |

> OHLC limit fills · fees on entry+exit · SL before TP on same bar
> Source: `engine/paper_simulator.py`
