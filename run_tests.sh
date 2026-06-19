#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PYTHONPATH="${ROOT}/backend${PYTHONPATH:+:${PYTHONPATH}}"

echo "==> Running unit tests..."
python -m pytest unit_tests/ -v "$@"

echo "==> Running API tests..."
python -m pytest API_tests/ -v "$@"

echo ""
echo "All tests passed."
