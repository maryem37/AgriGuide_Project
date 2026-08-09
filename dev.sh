#!/usr/bin/env bash
# Start local backend (DB + all agents). From repo root:
#   ./dev.sh
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  echo "Shared venv missing — running setup first..."
  ./scripts/setup_venv.sh
fi

docker compose up -d db
./.venv/bin/python scripts/run_backend.py
