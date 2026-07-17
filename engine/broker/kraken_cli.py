"""Optional kraken-cli subprocess broker."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, Dict, List, Optional


def kraken_available() -> bool:
  return shutil.which("kraken") is not None


def _run(args: List[str], timeout: int = 45) -> Dict[str, Any]:
  cmd = ["kraken", *args, "-o", "json"]
  proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
  raw = (proc.stdout or "").strip()
  if not raw:
    return {"ok": False, "exit_code": proc.returncode, "stderr": proc.stderr}
  try:
    data = json.loads(raw)
  except json.JSONDecodeError:
    return {"ok": proc.returncode == 0, "raw": raw, "stderr": proc.stderr}
  if proc.returncode != 0:
    return {"ok": False, "data": data, "stderr": proc.stderr}
  return {"ok": True, "data": data}


def paper_init(balance: float = 10000) -> dict:
  return _run(["paper", "init", "--balance", str(balance)])


def paper_buy(pair: str, volume: float, price: Optional[float] = None) -> dict:
  args = ["paper", "buy", pair, str(volume)]
  if price is not None:
    args.extend(["--type", "limit", "--price", str(price)])
  return _run(args)


def paper_sell(pair: str, volume: float, price: Optional[float] = None) -> dict:
  args = ["paper", "sell", pair, str(volume)]
  if price is not None:
    args.extend(["--type", "limit", "--price", str(price)])
  return _run(args)


def paper_status() -> dict:
  return _run(["paper", "status"])


def order_buy(pair: str, volume: float, *, price: float, validate: bool = False) -> dict:
  args = ["order", "buy", pair, str(volume), "--type", "limit", "--price", str(price)]
  if validate:
    args.append("--validate")
  return _run(args)


def order_sell(pair: str, volume: float, *, price: float, validate: bool = False) -> dict:
  args = ["order", "sell", pair, str(volume), "--type", "limit", "--price", str(price)]
  if validate:
    args.append("--validate")
  return _run(args)


def open_orders() -> dict:
  return _run(["open-orders"])


def cancel_all() -> dict:
  return _run(["order", "cancel-all"])


def balance() -> dict:
  return _run(["balance"])


def ticker(pair: str) -> dict:
  return _run(["ticker", pair])
