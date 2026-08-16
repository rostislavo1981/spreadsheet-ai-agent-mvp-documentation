#!/usr/bin/env bash
# Start the backend dev server.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=backend
exec python3 -m uvicorn app.main:create_app --factory \
  --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8000}" --reload
