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

### Cost comparison (typical critical advisory)

Assumes ~450 input tokens + ~180 output tokens per call (compact advisory JSON). Run live numbers:

```bash
python3 ew_tool.py --llm-cost
```

| Scenario | Models | Calls | Est. cost | When to use |
|---|---|---:|---:|---|
| **Single cheap** | `gpt-4o-mini` | 1 | ~$0.0002 | High-volume batch, `--llm-advisory-max` caps |
| **Ensemble agree** | mini + haiku | 2 | ~$0.0013 | Default — dual cheap screen, unanimous |
| **Ensemble disagree** | mini + haiku + `gpt-4o` | 3 | ~$0.0042 | Hard decisions — premium tiebreaker only |
| **Ensemble blended** (~30% disagree) | conditional | 2–3 | ~$0.0021 | Expected real-world cost |
| **Dual premium** ❌ | `gpt-4o` + sonnet | 2 | ~$0.0070 | Avoid — ~3× ensemble cost |
| **Cache hit** | — | 0 | $0 | Same symbol/verdict/price within 1h |

**Task → model tier** (cheap wherever possible):

| Task | Tier | Models |
|---|---|---|
| Advisory screen | cheap | `gpt-4o-mini`, `claude-3-5-haiku` |
| Tiebreaker (disagreement) | standard | `gpt-4o` or `claude-sonnet` |
| Architect / RepoMix review | standard | premium — complex multi-file reasoning |
| Post-batch synthesis | standard | premium — cross-pair executive summary |

Ensemble saves **~70%** vs dual premium while still using two cheap models + conditional premium.

## Cursor Pro vs direct API keys

**Important:** Cursor Pro model access and `ew_tool --llm-advisory` are **not the same billing path** today.

| Where models run | What you use | Billed from |
|---|---|---|
| **Cursor IDE / Cloud Agent** (this session) | Agent, Composer, Claude, GPT, Grok, etc. | Your **Cursor Pro** plan |
| **`ew_tool.py --llm-advisory`** (terminal/batch) | `OPENAI_API_KEY` + `ANTHROPIC_API_KEY` | **Direct API** (separate from Pro) |

### What Cursor Pro includes ([docs](https://cursor.com/docs/models-and-pricing))

Pro ($20/mo) gives **two usage pools** that reset monthly:

| Pool | Models | Good for |
|---|---|---|
| **First-party** (generous) | Auto, **Composer 2.5**, **Grok 4.5** | Cheap/high-volume — screen tasks, code, routine review |
| **API** ($20/mo included) | Claude, GPT, Gemini, etc. (frontier) | Tiebreakers, architect review, complex synthesis |

You can pick most frontier models in the IDE/agent UI. That access does **not** automatically flow into `ew_tool` Python scripts — those still need direct API keys unless we add a **Cursor SDK** backend (`CURSOR_API_KEY`).

### Recommended split (cheap vs premium)

| Task | Best runtime | Model tier |
|---|---|---|
| Run analysis pipeline (OKX fetch, EW, harmonics) | `ew_tool.py` | No LLM — deterministic |
| Advisory screen on GO setups | Cursor agent **or** `ew_tool --llm-advisory` | **Cheap** — Composer 2.5 / mini / haiku |
| Tiebreaker when models disagree | Cursor agent **or** ensemble tiebreaker | **Premium** — Sonnet / GPT-4o |
| Architect / RepoMix / multi-file design | **Cursor Cloud Agent** (here) | **Premium** — uses Pro pools |
| Top-50 batch + review top 5 GO setups | Cursor agent on batch JSON | **Premium** — one session, Pro pool |

### Cost mental model on Pro

For a typical advisory (~450 in / ~180 out tokens):

| Backend | Example model | Est. per call | Pool |
|---|---|---:|---|
| Cursor first-party | Composer 2.5 | ~$0.0007 | First-party (generous) |
| Direct API (current `ew_tool`) | gpt-4o-mini | ~$0.0002 | Your OpenAI bill |
| Cursor API pool | Claude Sonnet | ~$0.003 | Pro $20 API allowance |
| This Cloud Agent session | Multi-model panel | Included in Pro | IDE/agent usage |

**Practical takeaway:** Use **Cursor agents** (like this session) for architecture, batch review, and complex multi-model decisions — that is what Pro is for. Use **`ew_tool --llm-advisory`** only when you need unattended/automated advisory in CI or cron; then either bring your own API keys (cheap models) or we wire `EW_LLM_BACKEND=cursor` via the Cursor SDK (future).

```bash
# Check direct-API cost estimates (does not use Cursor Pro)
python3 ew_tool.py --llm-cost

# Cursor SDK path (future) — would use CURSOR_API_KEY + Pro pools
# export EW_LLM_BACKEND=cursor
# export CURSOR_API_KEY=...   # from cursor.com/dashboard
```


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
