#!/usr/bin/env bash
# Lint + type + unit/contract/integration checks (offline, no network/keys).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=backend
python3 -m ruff check backend/app || true
python3 -m mypy backend/app || true
python3 -m pytest backend/tests -q
