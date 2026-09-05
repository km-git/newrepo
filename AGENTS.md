# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Python CLI product: `ew_tool.py`, an Elliott Wave + harmonic
trading-analysis tool. Local stdlib dashboards (no Flask/FastAPI): `--monitor`
(`http://127.0.0.1:8765`) and `--monetize-ui` (Monetize Explorer at `/monetize`).

### Environment

- Use the project virtualenv at `.venv` (created during setup). Run Python via
  `.venv/bin/python` / `.venv/bin/pip`. The system Python is externally managed
  (PEP 668), so do not `pip install` into it.
- **One-shot bootstrap:** `bash scripts/setup_environment.sh` or
  `.venv/bin/python ew_tool.py --setup` — creates venv, installs `requirements.txt`,
  clones GitHub EW libs into `libs/`, installs token savers, and installs `gh` CLI.
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
- Monetize Explorer: `.venv/bin/python ew_tool.py --monetize-ui` → `http://127.0.0.1:8765/monetize`
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
- **Cheap-first AI routing (~95% Cursor Pro):** `engine/llm_budget_policy.py` — Composer/Grok/Grok High for ~95% of calls.
  Other Models (GPT/Claude/Gemini) capped at 2% for executive GO+high only — shame block at 5%.
  Env: `EW_CURSOR_PRO_ONLY=1`, `EW_LLM_CHEAP_TARGET_PCT=98`, `EW_OTHER_MODELS_BUDGET_PCT=2`,
  `EW_OTHER_MODELS_SHAME_PCT=5`, `EW_ALLOW_OTHER_MODELS=0`, `EW_USE_CURSOR_API_POOL=0`, `EW_MINIMIZE_GPT=1`.
  Matrix: `python3 ew_tool.py --llm-tasks`.
- **Resource gap audit (self-challenge):** `engine/resource_gap_audit.py` questions missing free data, TV OSS,
  GitHub tools, and Python libs each improvement cycle. CLI: `python3 ew_tool.py --gap-audit`.
  State: `output/system/resource_gap_audit.json`. Env: `EW_GAP_AUDIT=1`.
- **PR auto-approve:** `python3 ew_tool.py --pr-approve <N>` or `--pr-approve-all`.
  **Conflict auto-resolve:** `python3 ew_tool.py --pr-resolve-conflicts [N]` or `scripts/pr_auto_resolve_conflicts.py`.
  Agent: `python3 scripts/pr_executive_consensus.py`. 5/7 model consensus rule.
  GitHub Actions: `.github/workflows/pr-executive-consensus.yml`, `.github/workflows/pr-auto-resolve-conflicts.yml`.
  Results in `output/pr_reviews/`. Env: `EW_PR_AUTO_RESOLVE_CONFLICTS=1` (default on).
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
- **Effectiveness validation:** Prove geometry edge + fee-adjusted expectancy on resolved setups.
  CLI: `python3 ew_tool.py --effectiveness` or `PYTHONPATH=/workspace python3 scripts/run_effectiveness_validation.py`.
  Fast (no live OHLC paper): `--fast`. Reports: `reports/EFFECTIVENESS_VALIDATION.md`, `output/system/effectiveness_latest.json`.
  Gates: pytest subset, outcome WR ≥55%, 1h WR ≥70%, fitness ≥0.45, **wf_1h_fee_expectancy ≥0 R** (policy-filtered walk-forward), tracked fee backtest, impact discovery, health.
  Policy filters block weak TFs (1d/12h) and underperforming directions (LONG) by default — see `engine/execution_gates.py`.
- **Nightly AutoResearch:** Top-N batch → `--autoresearch-eval` → goal-mode quick.
  Script: `bash scripts/run_nightly_autoresearch.sh` (`EW_NIGHTLY_BATCH_N`, default 15).
  Workflow: `.github/workflows/autoresearch-nightly.yml` (03:00 UTC + manual dispatch); artifacts: `output/nightly/`, `experiments.jsonl`.
- **Autonomous daily ops:** Full self-improve loop: pytest → improvement/OKF → autoresearch → goal-mode → web/social intel → ready drafts + `--pr-approve-all` → summary JSON.
  CLI: `python3 ew_tool.py --autonomous-daily` or `bash scripts/run_autonomous_daily.sh`.
  **Daily trading ops (LLM-free):** `python3 ew_tool.py --daily-trading-tick` or `bash scripts/run_daily_trading_tick.sh` — paper proof + GOAT audit + tactical posture + health readiness.
  24h daemon: `bash scripts/run_autonomous_daemon.sh` (`EW_AUTONOMOUS_INTERVAL`, default 86400s).
  Workflow: `.github/workflows/autonomous-daily.yml` (04:00 UTC). Summary: `output/autonomous/daily/latest_summary.json`.
  Env: `EW_PR_AUTO_APPROVE=1`, `EW_PR_AUTO_MERGE=1`, `EW_PR_MERGE_WITHOUT_PANEL=1` (merge on rules-only APPROVE_MERGE when GitHub review API blocked).
  Set `CURSOR_API_KEY` in Cloud Agent secrets for full multi-model panel in CI/daily runs.
- **Executive intel (TV OSS + free data):** `engine/executive_intel.py` fuses Fear&Greed, WS imbalance, social signals, TV OSS stack, risk consensus, and impact discovery into board scores and execution consensus. Env: `EW_EXECUTIVE_INTEL=1`, `EW_DEEP_RESEARCH=1`, `EW_WEB_INTEL=1`, `EW_WS_ENABLED=1`, `EW_TV_OSS_CONSENSUS=1`.
- **V6 scanner (1000 pairs, 6 TFs):** Continuous large-scale validation across `15m,1h,4h,12h,1d,1w`.
  Universe: OKX spot USDT + USDT perps (~835 symbols max). Chunked scans rotate every 30 min; full refresh every 6h.
  CLI: `python3 ew_tool.py --v6-scan` (chunk) or `--v6-scan-full` (full universe).
  Scripts: `python3 scripts/run_v6_scanner.py`, `bash scripts/run_v6_scanner_daemon.sh` (24/7).
  Best trades: `output/v6_scanner/best_trades_latest.json`. Env: `EW_V6_SETUP=1`, `EW_SCANNER_PAIRS=1000`, `EW_SCANNER_CHUNK=50`.
- **Universe scanner (main, PR #13):** Overlapping 24/7 chunked scanner via `engine/universe_scanner.py`.
  CLI: `python3 scripts/run_universe_247.py`, `bash scripts/run_universe_daemon.sh`.
  Timeframes: `engine/timeframes.py` (`UNIVERSE_TFS`). Best trades: `output/latest_universe_best_trades.csv`.
  Note: v6_scanner and universe_scanner coexist post-merge — consolidate in a follow-up (see PR #12).
