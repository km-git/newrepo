# Elliott Wave + Harmonic Trading Analysis Agent

CLI tool for Elliott Wave impulse validation (strict R1/R2/R3), ABC correction detection, harmonic XABCD confluence, and trade setup generation with honest abstention.

## Features

- **Multi-timeframe pipeline** (1w → 15m): HTF bias, adaptive MonoWaves, kill zone clustering, harmonic overlay, execution validation
- **Strict rule enforcement**: R1/R2/R3 are hard gates; no rule relaxation for standard impulses
- **Token-saving infrastructure** for Cursor agents:
  - **Compressed disk cache** (`zstd` + `msgpack` + `diskcache`) for OHLCV, monowaves, harmonics, Monte Carlo
  - **Semantic gateway cache** (Cloudflare AI Gateway pattern) for repetitive OKX OHLCV queries
  - **RepoMix export** (`--repomix`) minifies code structures for LLM agent context
  - **Deduplication** of harmonic patterns, monowaves, and tool-call logs
  - **Result hashing** in `tool_calls_log` — full payloads stored by hash, not inlined in JSON
- **Exchange**: OKX only for live crypto OHLCV (avoids Bybit/Binance geo-blocks)
- **Pydantic v2** validated JSON output

## Quick Start

```bash
pip install -r requirements.txt

# Clone GitHub libs (one-time)
git clone --depth 1 https://github.com/niall-oc/pyharmonics.git libs/pyharmonics
git clone --depth 1 https://github.com/drstevendev/ElliottWaveAnalyzer.git libs/ElliottWaveAnalyzer
git clone --depth 1 https://github.com/DrEdwardPCB/python-taew.git libs/python-taew
pip install -e libs/python-taew libs/pyharmonics

# Single symbol (crypto) — OKX live data + semantic gateway cache
python3 ew_tool.py --symbol BTC/USDT --crypto --gateway-stats

# Critical decision: second opinion from Claude + GPT (requires API keys)
export OPENAI_API_KEY=... ANTHROPIC_API_KEY=...
python3 ew_tool.py --symbol BTC/USDT --crypto --llm-advisory

## Multi-model intelligence panel (default with `--llm-advisory`)

When `--llm-advisory` is enabled, the tool uses **ensemble mode** by default — similar to Cursor's multi-model approach:

| Phase | Models | When |
|---|---|---|
| **1. Cheap screen** | `gpt-4o-mini` + `claude-3-5-haiku` in parallel | Both API keys present |
| **2. Premium tiebreaker** | `gpt-4o` or `claude-sonnet` (one call) | Cheap models disagree |
| **3. Confidence apply** | Panel adjustment applied to `trade_setup.confidence` | Always (audit trail preserved) |

Set `EW_LLM_INTELLIGENCE=single` for token-minimal single-model mode, or `dual` for cheap dual screen without tiebreaker.

## Token-efficient LLM advisory

LLM calls are gated to **critical decisions only** and use these token-saving mechanisms:

| Mechanism | What it does |
|---|---|
| **Critical-only gate** | Skips LLM for monitor/STANDBY setups (~90% of batch pairs) |
| **Ensemble default** | `EW_LLM_INTELLIGENCE=ensemble` — dual cheap screen, premium only on disagreement |
| **Single provider fallback** | Falls back to one model when only one API key is set |
| **Cheap tier default** | Screen uses mini/haiku — premium only for tiebreaker |
| **Compact prompts** | Short JSON keys (`sym`, `v`, `dir`) — ~60% fewer input tokens |
| **Output cap** | `EW_LLM_MAX_OUTPUT=280` (default) — advisory JSON is small |
| **Anthropic prompt cache** | System prompt uses `cache_control: ephemeral` on repeat calls |
| **Disk cache (1h)** | Same symbol/verdict/price → zero API tokens |
| **Batch cap** | `--llm-advisory-max 5` limits consultations per batch run |
| **Pipeline token store** | `tool_calls_log` stores hashes, not full payloads (`cache/TokenStore`) |
| **Semantic OHLCV cache** | OKX data reused across pairs/runs — no redundant market fetches |
| **RepoMix export** | `--repomix` minifies codebase for agent context |

```bash
# Default with --llm-advisory: ensemble (dual cheap + premium tiebreaker)
export EW_LLM_INTELLIGENCE=ensemble   # ensemble | single | dual
export OPENAI_API_KEY=... ANTHROPIC_API_KEY=...

# Token-minimal: one cheap model
export EW_LLM_INTELLIGENCE=single
export EW_LLM_PROVIDER=auto          # auto | openai | anthropic | dual
export EW_LLM_TIER=cheap             # cheap | standard
export EW_LLM_MAX_OUTPUT=280

# Legacy dual without tiebreaker
export EW_LLM_INTELLIGENCE=dual
```

# Batch with up to 5 LLM consultations on GO / CONDITIONAL_GO pairs
python3 scripts/run_top50_batch.py -n 50 --llm-advisory --llm-advisory-max 5

# RepoMix-style code pack for agent context
python3 ew_tool.py --repomix --repomix-out output/repomix_pack.xml

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

## Multi-Engine EW Consensus (Step 6)

Aggregates signals from GitHub Elliott Wave libraries for additional confidence:

| Engine | Source | Role |
|--------|--------|------|
| `internal_1d/4h/15m` | `core/impulse.py` | Strict R1/R2/R3 per timeframe |
| `ewa_impulse` | [ElliottWaveAnalyzer](https://github.com/drstevendev/ElliottWaveAnalyzer) | Impulse + leading diagonal scan |
| `ewa_correction` | ElliottWaveAnalyzer | ABC correction from swing high |
| `taew_fib` | [python-taew](https://github.com/DrEdwardPCB/python-taew) | Wave 2–5 Fibonacci validation |

Output `step6_wave_consensus` includes `consensus_direction`, `agreement_pct`, per-engine votes, and divergences. Executive confidence is boosted when engines agree.

## Output Status (Executive Mode)

The agent behaves as an expert trader and **always produces an actionable plan**. Structural gaps are disclosed but never block a decision.

| Status | Verdict | Meaning |
|--------|---------|---------|
| `execute` | GO | Full confluence — enter now at full size |
| `conditional_execute` | CONDITIONAL_GO | In zone, partial confirmation — 50% probe + add on trigger |
| `active_monitor` | STANDBY_ORDERS | Harmonic PRZ defined — GTC limits placed |
| `staged_entry` | STAGED_GO | Scale-in across probe → fib → kill zone levels |

Every output includes `executive_decision` with verdict, conviction, playbook, contingencies, and scale legs when applicable.

## Cache Environment

Set `EW_CACHE_DIR` to override default `.cache/ew_tool`.
