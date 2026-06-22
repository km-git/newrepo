"""Multi-instrument batch runner with shared cache and deduplicated output."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from cache.disk_cache import get_cache
from engine.adaptive import adaptive_pipeline
from schemas.models import ElliottWaveOutput


def run_batch(csv_path: str, tfs: List[str], is_crypto: bool) -> List[dict]:
  path = Path(csv_path)
  if not path.exists():
    raise FileNotFoundError(csv_path)

  symbols: List[tuple[str, bool]] = []
  with path.open() as f:
    reader = csv.DictReader(f)
    for row in reader:
      sym = row.get("symbol") or row.get("Symbol") or row.get("SYMBOL")
      if not sym:
        continue
      crypto_flag = row.get("crypto", "").lower() in ("1", "true", "yes")
      symbols.append((sym.strip(), crypto_flag if row.get("crypto") else is_crypto))

  results: List[dict] = []
  for symbol, crypto in symbols:
    print(f"\n[batch] === {symbol} (crypto={crypto}) ===")
    try:
      raw = adaptive_pipeline(symbol, tfs, crypto)
      validated = ElliottWaveOutput(**raw)
      results.append(validated.model_dump())
    except Exception as e:
      results.append({"symbol": symbol, "status": "incomplete", "error": str(e)})

  print(f"\n[batch] completed {len(results)} instruments, cache={get_cache().stats()}")
  return results


def save_batch_json(results: List[dict], out_path: str) -> None:
  with open(out_path, "w") as f:
    json.dump(results, f, indent=2, default=str)
