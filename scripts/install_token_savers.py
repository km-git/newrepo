#!/usr/bin/env python3
"""Install token-saving Python libraries from web-researched registry."""

from __future__ import annotations

import json
import sys

from engine.token_saver_registry import install_missing_libraries, registry_summary


def main() -> None:
  upgrade = "--upgrade" in sys.argv
  result = install_missing_libraries(upgrade=upgrade)
  out = {"install": result, "registry": registry_summary()}
  print(json.dumps(out, indent=2))
  if result.get("still_missing"):
    sys.exit(1)


if __name__ == "__main__":
  main()
