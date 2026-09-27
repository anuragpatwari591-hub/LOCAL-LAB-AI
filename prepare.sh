#!/usr/bin/env bash
# LOCAL-LAB-AI - one-time preparation (Linux/macOS). Requires internet access.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
export LOCAL_LAB_AI_ROOT="$SCRIPT_DIR"
cd "$SCRIPT_DIR"

PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "[LOCAL-LAB-AI] ERROR: no Python interpreter found on PATH." >&2
  echo "Install Python 3.10+ first (e.g. 'sudo apt install python3 python3-venv'), then re-run prepare." >&2
  exit 1
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/scripts/prepare_main.py" "$@"
