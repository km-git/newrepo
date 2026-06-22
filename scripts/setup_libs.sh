#!/usr/bin/env bash
# Clone GitHub dependencies (shallow) and install in editable mode.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/libs"

clone_if_missing() {
  local url="$1" dest="$2"
  if [ ! -d "$dest/.git" ]; then
    git clone --depth 1 "$url" "$dest"
  fi
}

clone_if_missing "https://github.com/niall-oc/pyharmonics.git" "$ROOT/libs/pyharmonics"
clone_if_missing "https://github.com/drstevendev/ElliottWaveAnalyzer.git" "$ROOT/libs/ElliottWaveAnalyzer"
clone_if_missing "https://github.com/DrEdwardPCB/python-taew.git" "$ROOT/libs/python-taew"

# python-taew needs README for setup.py
[ -f "$ROOT/libs/python-taew/README.md" ] || echo "# python-taew" > "$ROOT/libs/python-taew/README.md"

pip install -e "$ROOT/libs/python-taew" -e "$ROOT/libs/pyharmonics"
pip install -r "$ROOT/requirements.txt"

python3 -c "from taew import wave2_fibonacci_check; print('taew OK')"
python3 -c "from pyharmonics.technicals import OHLCTechnicals; print('pyharmonics OK')"
echo "Setup complete."
