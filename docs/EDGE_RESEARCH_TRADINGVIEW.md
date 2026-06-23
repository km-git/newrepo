# Edge Research: TradingView Open-Source Scripts vs Current System

## Executive summary

The current system is **structure-first (Elliott Wave)** with a **thin momentum overlay** (RSI/EMA/MACD/volume). System audit shows **OOS avg 48%** and only **1/200 executable** setups because crypto rarely passes strict R1 impulse rules.

TradingView's open-source ecosystem offers **orthogonal edge layers** that do not require perfect 5-wave counts. The highest-impact integrations are:

| Priority | OSS Source | Edge Type | Why it matters |
|----------|-----------|-----------|----------------|
| **P0** | [CedInvest/sm-radar-pine](https://github.com/CedInvest/sm-radar-pine) | SMC: BOS/CHoCH, OB, FVG | Bypasses EW impulse bottleneck; crypto-native |
| **P0** | [LuxAlgo MSB & OB Toolkit](https://www.tradingview.com/script/ObcbP092-Market-Structure-Break-OB-Probability-Toolkit-LuxAlgo/) | Momentum-filtered MSB + OB probability | Z-score conviction filter on structure breaks |
| **P1** | [mihakralj/QuanTAlib](https://github.com/mihakralj/QuanTAlib) | 393 indicators, Pine/Python parity | ADX, SuperTrend, Williams %R, Stochastic — missing from our stack |
| **P1** | [damianpitt/capital41-indicators](https://github.com/damianpitt/capital41-indicators) | Divergence + perp stress | RSI/Williams divergence; funding/basis stress |
| **P2** | [Ahmed-GoCode/Quant-Edge-Indicators](https://github.com/Ahmed-GoCode/Quant-Edge-Indicators) | MSS + CHoCH + FVG + RSI multilayer | Confirms SMC stack |
| **P2** | [LuxAlgo/PineTS](https://github.com/LuxAlgo/PineTS) | Run Pine Script outside TV | Future: port invite-only scripts to batch pipeline |

## What we had (dark space diagnosis)

### Blind spots
1. **No market structure layer** — only Elliott impulse R1/R2/R3 (fails on deep crypto W2 retracements)
2. **No order flow / liquidity** — orderbook + funding exist in code but are **never wired** (`exchange=None`)
3. **17 calibration tokens** — ledger shows `in kill zone` at 45.7% WR, `harmonic PRZ` at 9.5% WR (blocked correctly)
4. **No ADX / SuperTrend / regime filter** — trending vs mean-reverting not distinguished at execution gate
5. **No divergence engine** — simple RSI div only in legacy `market_tools`, disabled under calibration
6. **Zero TradingView / Pine integration** — no OSS script parity

### Why OOS stays at 48%
- Executable label requires `impulse_valid AND NOT partial` → **9 valid / 200 setups**
- Walk-forward uses same EW+indicator logic that fails IS on most pairs
- Paper win rate 41% confirms signals are not yet predictive at scale

## OSS scripts that can outperform our stack (by layer)

### Layer 1: Smart Money Concepts (game changer)
**Source:** SM Radar (MPL-2.0), LuxAlgo MSB toolkit (open-source on TV)

| Concept | Our system | OSS approach |
|---------|-----------|--------------|
| Structure break | EW R1/R2/R3 only | BOS (continuation) + CHoCH (reversal) on pivot breaks |
| Entry zone | Fib kill zone | Order Block = last opposing candle before impulsive BOS |
| Imbalance | Harmonic PRZ (9.5% WR) | Fair Value Gap = 3-candle inefficiency |
| Liquidity | Not modeled | Equal highs/lows, PDH/PDL, session boxes |

**Implementation:** `core/smc_structure.py` — ported from SM Radar logic.

**New execution path:** `SMC FULL` in `readiness.py` when `smc_valid + smc_aligned + in_zone + OOS pass` — **no EW impulse required**.

### Layer 2: QuanTAlib enhanced dynamics
**Source:** [mihakralj/QuanTAlib](https://github.com/mihakralj/QuanTAlib) — same math in Pine v6 and Python (`pip install quantalib`)

| Indicator | Use |
|-----------|-----|
| ADX | Trend strength gate (avoid chop) |
| SuperTrend | Directional filter |
| Williams %R | Oversold/overbought + divergence (capital41 style) |
| Momentum Z-score | LuxAlgo MSB toolkit conviction filter |
| Stochastic | Secondary oscillator confirmation |

**Implementation:** `core/tv_enhanced.py`

### Layer 3: Crypto-specific (not yet wired)
**Sources:** capital41 Crypto Perp Stress, mxdvt07 Funding Rate Aggregated

| Signal | Edge |
|--------|------|
| Funding rate extreme | Crowded positioning → fade or avoid |
| Basis (spot vs perp) | Stress / squeeze detection |
| OI impulse | Liquidation cascade risk |

**Next step:** Pass `exchange` to `build_market_confluence()` in batch pipeline.

### Layer 4: PineTS (future)
**Source:** [LuxAlgo/PineTS](https://github.com/LuxAlgo/PineTS)

Run Pine Script v5/v6 indicators on our OHLCV in Node.js with 1:1 syntax. Enables porting LuxAlgo Library scripts (largest OSS indicator collection) without manual Python reimplementation.

## Integration architecture (implemented)

```
FETCH OHLCV
    ↓
EW matrix (existing)          SMC matrix (NEW: sm-radar logic)
    ↓                              ↓
QuanTAlib enhanced (NEW)  ←── merge in tv_edge.py
    ↓
readiness.py: EW FULL | SMC FULL | PROBE | monitor
    ↓
calibration ledger learns new tokens (SMC BOS bull, in bullish OB, ADX trend strong, ...)
```

### New files
| File | Role |
|------|------|
| `core/smc_structure.py` | BOS/CHoCH, Order Blocks, FVG |
| `core/tv_enhanced.py` | QuanTAlib ADX, SuperTrend, Williams, divergence |
| `engine/tv_edge.py` | Orchestrator + token merge |
| `engine/adaptive.py` step 7b | Pipeline hook |

## Recommended rollout

### Phase 1 (done)
- SMC + QuanTAlib layer wired into pipeline
- SMC FULL execution path
- `quantalib` in requirements

### Phase 2 (next)
- Wire `exchange` for funding + orderbook in batch
- Add capital41-style Williams + RSI dual divergence
- Calibrate new SMC tokens from paper ledger (100+ trades)
- Re-run brutal batch; target OOS avg > 52%

### Phase 3
- PineTS pilot: port LuxAlgo MSB Z-score filter exactly
- Session liquidity (Asia/London/NY from SM Radar)
- Equal highs/lows sweep detection

## Honest expectations

No OSS script guarantees alpha. The edge comes from:
1. **Orthogonal signals** (SMC structure when EW fails)
2. **Regime filtering** (ADX/SuperTrend avoid chop)
3. **Ledger-calibrated weighting** (keep what works, block anti-predictive)
4. **OOS gating** (never trust IS-only)

Scripts to **avoid**: repainting indicators without `barstate.isconfirmed`, "100% win rate" strategies, copied forum folklore (use mihakralj's mathematically grounded implementations instead).

## Key OSS repositories

- https://github.com/CedInvest/sm-radar-pine — SMC crypto (MPL-2.0)
- https://github.com/mihakralj/QuanTAlib — 393 indicators, Python + Pine
- https://github.com/mihakralj/pinescript — Pine v6 source mirror
- https://github.com/damianpitt/capital41-indicators — OB, divergence, perp stress
- https://github.com/Ahmed-GoCode/Quant-Edge-Indicators — MSS, FVG, RSI multilayer
- https://github.com/LuxAlgo/PineTS — Run Pine anywhere
- https://www.tradingview.com/script/ObcbP092- — LuxAlgo MSB open-source
