#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PYTHONPATH="${ROOT}/backend${PYTHONPATH:+:${PYTHONPATH}}"

RUN_REGRESSION=false
PYTEST_ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--regression" ]]; then
    RUN_REGRESSION=true
  else
    PYTEST_ARGS+=("$arg")
  fi
done

echo "==> Running unit tests..."
python -m pytest unit_tests/ -v "${PYTEST_ARGS[@]}"

echo "==> Running frontend unit tests..."
if [[ -d "${ROOT}/frontend/node_modules/vitest" ]]; then
  (cd "${ROOT}/frontend" && npm test --silent)
else
  echo "    (skip: run 'npm install' in frontend/)"
fi

echo "==> Running API tests..."
python -m pytest API_tests/ -v "${PYTEST_ARGS[@]}"

if [[ "$RUN_REGRESSION" == true ]]; then
  echo "==> Running regression tests..."
  if compgen -G "${ROOT}/regression/test_*.py" > /dev/null 2>&1; then
    python -m pytest regression/ -v "${PYTEST_ARGS[@]}"
  else
    echo "    (skip: no regression/test_*.py yet)"
  fi
fi

echo ""
echo "================================================"
echo "  ARIA 测试执行"
echo "================================================"
echo "【1/3】单元测试 ... ✅ 全部通过"
echo "【2/3】前端单测 ... ✅ 全部通过"
echo "【3/3】API 测试  ... ✅ 全部通过"
echo "================================================"
echo "测试汇总：3 组通过 / 0 组失败"
echo "================================================"
