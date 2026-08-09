#!/usr/bin/env bash
# One-time setup of the shared project virtualenv (macOS/Linux).
# Usage (from repo root):
#   ./scripts/setup_venv.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  echo "Creating .venv ..."
  python3 -m venv .venv
fi

./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

echo
echo "Optional Agriculture ML stack (chromadb/torch) — install with:"
echo "  ./.venv/bin/python -m pip install -r requirements-ml.txt"
echo
echo "Then start everything with:"
echo "  docker compose up -d db"
echo "  ./.venv/bin/python scripts/run_backend.py"
