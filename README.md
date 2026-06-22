# Elliott Wave + Harmonic Trading Analysis Agent

CLI tool for Elliott Wave impulse validation (strict R1/R2/R3), ABC correction detection, harmonic XABCD confluence, and trade setup generation with honest abstention.

## Features

- **Multi-timeframe pipeline** (1w → 15m): HTF bias, adaptive MonoWaves, kill zone clustering, harmonic overlay, execution validation
- **Strict rule enforcement**: R1/R2/R3 are hard gates; no rule relaxation for standard impulses
- **Token-saving infrastructure** for Cursor agents:
  - **Compressed disk cache** (`zstd` + `msgpack` + `diskcache`) for OHLCV, monowaves, harmonics, Monte Carlo
  - **Deduplication** of harmonic patterns, monowaves, and tool-call logs
  - **Result hashing** in `tool_calls_log` — full payloads stored by hash, not inlined in JSON
- **Exchange fallback**: okx → bybit → kraken → binance (avoids Binance HTTP 451)
- **Pydantic v2** validated JSON output

## Quick Start

```bash
pip install -r requirements.txt

# Clone GitHub libs (one-time)
git clone --depth 1 https://github.com/niall-oc/pyharmonics.git libs/pyharmonics
git clone --depth 1 https://github.com/drstevendev/ElliottWaveAnalyzer.git libs/ElliottWaveAnalyzer
git clone --depth 1 https://github.com/DrEdwardPCB/python-taew.git libs/python-taew
pip install -e libs/python-taew libs/pyharmonics

# Single symbol (crypto)
python3 ew_tool.py --symbol BTC/USDT --crypto --cache-stats

# Batch mode
python3 ew_tool.py --batch samples/batch_symbols.csv --crypto --save out.json

# Run tests
python3 -m pytest tests/ -v
```

## Architecture

```
ew_tool.py                 # CLI entry point
├── cache/                 # zstd compression, dedup, token store
├── fetchers/              # ccxt + yfinance with caching
├── core/                  # ATR, monowaves, impulse, correction, harmonics, MC
├── schemas/               # Pydantic models
├── engine/                # adaptive pipeline + batch runner
└── tests/                 # R1/R2/R3 unit tests
```

## Output Status

| Status | Meaning |
|--------|---------|
| `execute` | Price in kill zone + 15m impulse passes R1/R2/R3 |
| `monitoring` | Harmonic overlap but price outside zone |
| `abstain` | No confluence — `trade_setup.action = no_trade` |
| `incomplete` | Fetch or pipeline error |

## Cache Environment

Set `EW_CACHE_DIR` to override default `.cache/ew_tool`.
