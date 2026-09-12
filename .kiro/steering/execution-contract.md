# Execution contract steering

## WATCH vs EXECUTE

- **WATCH**: setup detected; no order placement; may appear in analysis exports.
- **EXECUTE**: passes geometry hard-gates, direction/regime policy, and paper gates.

## Geometry

- Stop-loss must be on the correct side of entry for direction.
- Take-profit ladder order must be monotonic (TP1 closer than TP2, etc.).
- Timeframe caps: `1d` and `12h` blocked by default (`EW_BLOCKED_TFS`).
- Direction gates and regime gates on by default for paper and live.

## Paper simulation

- Queue-based sim with `as_of` backfill for forward ledger.
- Skip symbols with no OHLC (`no_ohlc`).
- Prefer major pairs; learned blocklist in `engine/paper_policy.py`.
- Relaxed paper gates only when `EW_PAPER_RELAX_GATES=1` (proof loop sets this).

## Live execution

- Paper is default. Live requires `EW_EXECUTE_CONFIRM=1` and Kraken API keys.
- Never commit credentials or raw account payloads.

## Accuracy claims

Valid only when:

1. Pair×TF resolved outcomes with n≥5, or
2. 30-day paper-forward ledger with documented methodology.

Do not cite global win rates from unstratified dense tables.
