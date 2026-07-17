# Paper Execution P&L

**Run:** 2026-07-17T15:37:42.316079+00:00  
**Equity:** $50,000.00 → $49,042.48  
**Realized P&L:** $-957.52  
**Fees:** $426.27 @ 0.26%  
**Max positions:** 3  

## Summary

| Metric | Value |
|--------|-------|
| Executable candidates | 61 |
| Simulated (cap) | 3 |
| Blocked | 58 |
| Wins | 0 |
| Losses | 3 |
| No fill | 0 |

## Simulated Trades

| Symbol | TF | Tier | Status | Legs | P&L $ | Fees $ | Avg entry |
|--------|-----|------|--------|------|-------|--------|-----------|
| BTC/USDT | 15m | full | closed_sl | 1/1 | $-542.32 | $292.32 | 59928.70261225 |
| NEAR/USDT | 15m | full | closed_sl | 1/1 | $-357.64 | $107.64 | 1.806907 |
| ADA/USDT | 15m | probe | closed_sl | 1/1 | $-57.56 | $26.31 | 0.14768944 |

## Blocked (portfolio / gates)

| Symbol | TF | Reasons |
|--------|-----|---------|
| AGLD/USDT | 15m | max_positions=3 |
| ALLO/USDT | 15m | max_positions=3 |
| ENA/USDT | 15m | max_positions=3 |
| G/USDT | 15m | max_positions=3 |
| GRAM/USDT | 15m | max_positions=3 |
| JTO/USDT | 15m | max_positions=3 |
| LIT/USDT | 15m | max_positions=3 |
| NES/USDT | 15m | max_positions=3 |
| PI/USDT | 15m | max_positions=3 |
| RE/USDT | 15m | max_positions=3 |
| XAUT/USDT | 15m | max_positions=3 |
| XRP/USDT | 15m | max_positions=3 |
| AAVE/USDT | 1h | max_positions=3 |
| ADA/USDT | 1h | max_positions=3 |
| AGLD/USDT | 1h | max_positions=3 |
| ALLO/USDT | 1h | max_positions=3 |
| BTC/USDT | 1h | max_positions=3 |
| CARDS/USDT | 1h | max_positions=3 |
| DOT/USDT | 1h | max_positions=3 |
| ENA/USDT | 1h | max_positions=3 |
| G/USDT | 1h | max_positions=3 |
| GRAM/USDT | 1h | max_positions=3 |
| JTO/USDT | 1h | max_positions=3 |
| LIT/USDT | 1h | max_positions=3 |
| NEAR/USDT | 1h | max_positions=3 |
| NES/USDT | 1h | max_positions=3 |
| PI/USDT | 1h | max_positions=3 |
| RE/USDT | 1h | max_positions=3 |
| XAUT/USDT | 1h | max_positions=3 |
| XRP/USDT | 1h | max_positions=3 |
| … | … | +28 more |

> OHLC limit fills · fees on entry+exit · SL before TP on same bar
> Source: `engine/paper_simulator.py`
