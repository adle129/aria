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
echo "================================================"
echo "  ARIA 测试执行"
echo "================================================"
echo "【1/2】单元测试 ... ✅ 全部通过"
echo "【2/2】API 测试  ... ✅ 全部通过"
echo "================================================"
echo "测试汇总：2 组通过 / 0 组失败"
echo "================================================"
