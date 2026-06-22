# Trade Setups Reports

The **trade setups table** is generated when you run a batch or the autodream daemon.

## View here (in the repo)

Open **[TRADE_SETUPS.md](./TRADE_SETUPS.md)** — markdown table with all scalp / day / swing / long-term setups.

## Full interactive table (local, after batch)

| File | Description |
|------|-------------|
| `output/latest_analysis.html` | Full confluences + 4 setups per pair (browser) |
| `output/latest_setups.csv` | One row per pair × style (Excel/Sheets) |
| `output/latest_analysis.csv` | One wide row per pair (149 columns) |

## Elliott Wave — always on

Every batch run analyzes **all 5 timeframes** (`1w, 1d, 4h, 1h, 15m`) for **every pair**:

- Adaptive monowave extraction with skip fallback (thin data → more waves)
- Per-TF structure: impulse / ABC / diagonal / invalid — never omitted
- `step2_ew_coverage` in JSON shows `coverage_pct` and `structures_by_tf`

Supplementary tools (RSI stack, VWAP, divergence, BTC correlation) layer on top — EW is never skipped.

```bash
# One-time full batch
PYTHONPATH=/workspace python3 scripts/run_top50_batch.py -n 50

# Scheduled refresh (monitor + batch every hour)
./scripts/run_autodream_daemon.sh

# Show paths
PYTHONPATH=/workspace python3 scripts/show_latest_analysis.py
```

> `output/` is gitignored (large, changes often). `reports/TRADE_SETUPS.md` is committed so you can always see the latest setups snapshot in the repo after a batch.
