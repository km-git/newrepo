# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Python CLI product: `ew_tool.py`, an Elliott Wave + harmonic
trading-analysis tool. There is no web/GUI service — everything is terminal-driven.

### Environment

- Use the project virtualenv at `.venv` (created during setup). Run Python via
  `.venv/bin/python` / `.venv/bin/pip`. The system Python is externally managed
  (PEP 668), so do not `pip install` into it.
- Three runtime dependencies are external GitHub repos cloned into `libs/`
  (`pyharmonics`, `ElliottWaveAnalyzer`, `python-taew`). They are gitignored and
  installed by the startup/update script — do not commit them.
- `ElliottWaveAnalyzer` is NOT pip-installed; it is loaded by adding `libs/ElliottWaveAnalyzer`
  to `sys.path` via `libs/ewa_patch.py`. `pyharmonics` pins older `yfinance`/`msgpack`/`urllib3`
  versions; this is expected and fine.

### Running / testing

- Tests: `.venv/bin/python -m pytest tests/ -v` (run from repo root). No linter is configured.
- Single symbol (live data fetch): `.venv/bin/python ew_tool.py --symbol BTC/USDT --crypto`
- Batch: `.venv/bin/python ew_tool.py --batch samples/batch_symbols.csv --crypto`
- The CLI and `pytest` work from the repo root without `PYTHONPATH`, but the helper
  scripts under `scripts/` (e.g. `scripts/run_top50_batch.py`, `scripts/show_latest_analysis.py`)
  require `PYTHONPATH=/workspace`.

### Gotchas

- Live runs fetch OHLCV from exchanges with fallback okx → bybit → kraken → binance, so
  network access is required and exact numeric output varies run-to-run. Binance returns
  HTTP 451; the fallback handles it.
- Output/cache dirs (`output/`, `.cache/ew_tool`) are gitignored. Override cache location
  with `EW_CACHE_DIR`.
- **Token budget is critical.** Each model capped at 10,000 tokens/day (`EW_LLM_MAX_TOKENS_PER_MODEL`).
  Install saver libraries: `python3 ew_tool.py --install-token-savers` or `python3 scripts/install_token_savers.py`.
  Inspect: `python3 ew_tool.py --llm-savers`.
- **PR auto-approve:** `python3 ew_tool.py --pr-approve <N>` or `--pr-approve-all`.
  Agent: `python3 scripts/pr_executive_consensus.py`. 5/7 model consensus rule.
  GitHub Action: `.github/workflows/pr-executive-consensus.yml`. Results in `output/pr_reviews/`.
- **OKF secondary brain:** Multi-model consensus persisted as OKF v0.1 concepts in `okf/brain/`.
  Self-improvement loop writes autodream lessons + honesty audits after each run.
  CLI: `--brain-ask "..."`, `--brain-search "..."`, `--brain-status`.
  Env: `EW_OKF_BRAIN=1`, `EW_BRAIN_CONSENSUS=1`, `EW_BRAIN_SELF_IMPROVE=1`, `EW_OKF_BRAIN_DIR` (optional).
- **Live execution stack:** Paper default. `python3 ew_tool.py --execute` (dry/paper) or `--execute-live` with
  `EW_EXECUTE_CONFIRM=1` + `KRAKEN_API_KEY`/`KRAKEN_API_SECRET`. Status: `--execution-status`.
  Data hub: WebSocket tickers (`EW_WS_ENABLED=1`), rotating proxies (`EW_PROXY_LIST`), web intel
  (`--data-intel BTC/USDT`). Script: `python3 scripts/execute_limit_orders.py --status`.
- **E2E continuous improvement:** Full cycle: learn → analyze → export → execute → improve.
  `python3 ew_tool.py --e2e-cycle --e2e-batch 50` or `python3 scripts/e2e_trading_cycle.py`.
  Daemon: `./scripts/run_e2e_daemon.sh`. Status: `--e2e-status`, `--health`.
  CI: `.github/workflows/ci.yml` + scheduled `.github/workflows/e2e-improvement.yml`.
