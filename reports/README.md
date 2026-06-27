# Trade Setups Reports

The **trade setups table** is generated when you run a batch or the autodream daemon.

## View here (in the repo)

| File | Description |
|------|-------------|
| **[TRADE_SETUPS.md](./TRADE_SETUPS.md)** | Style setups (scalp / day / swing / long) |
| **[COMPLETE_TRADING_ANALYSIS.md](./COMPLETE_TRADING_ANALYSIS.md)** | Full pair×TF book with dollar legs @ equity |
| **[trade_setups_matrix.html](./trade_setups_matrix.html)** | Shaded 50×5 grid — open in browser |
| **[latest_executable_pair_tf.csv](./latest_executable_pair_tf.csv)** | 61 executable rows only (Excel/Sheets) |

## Full interactive table (local, after batch)

| File | Description |
|------|-------------|
| `output/latest_trade_setups_matrix.html` | **Shaded 50×5 pair×TF grid** (FULL / PROBE / monitor / watch) |
| `output/latest_analysis.html` | Full confluences + 4 setups per pair (browser) |
| `output/latest_setups.html` | All style setups, row color-coded |
| `output/latest_setups.csv` | One row per pair × style (Excel/Sheets) |
| `output/COMPLETE_TRADING_ANALYSIS.md` | Full markdown book with dollar-sized legs |

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

# Regenerate from saved batch JSON (limit orders + matrix + markdown)
PYTHONPATH=/workspace python3 scripts/generate_complete_analysis.py --equity 50000 --usdt-d 8.2

# Show paths
PYTHONPATH=/workspace python3 scripts/show_latest_analysis.py
```

> `output/` is gitignored (large, changes often). `reports/TRADE_SETUPS.md` is committed so you can always see the latest setups snapshot in the repo after a batch.
