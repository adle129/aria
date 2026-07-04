#!/usr/bin/env bash
# Reassemble aria-deploy.tar.gz from split parts in /tmp/
# Usage: bash scripts/combine-deploy-package.sh

set -euo pipefail

OUT="/tmp/aria-deploy.tar.gz"
shopt -s nullglob
parts=(/tmp/aria-deploy.part*)
if [ ${#parts[@]} -eq 0 ]; then
  echo "ERROR: no /tmp/aria-deploy.part* files found. Upload split parts first."
  exit 1
fi

echo "==> Combining ${#parts[@]} part(s) -> $OUT"
cat "${parts[@]}" > "$OUT"
ls -lh "$OUT"

if ! tar -tzf "$OUT" | grep -q './deploy-stamp.txt'; then
  echo "WARN: deploy-stamp.txt missing — tarball may be old or corrupt."
  echo "      On Windows re-run: .\\scripts\\package-aliyun-deploy.ps1"
else
  echo "==> OK: deploy-stamp.txt present"
  tar -xzf "$OUT" -O ./deploy-stamp.txt
fi

echo ""
echo "Next:"
echo "  sudo tar -xzf $OUT -C /opt/aria"
echo "  cd /opt/aria && sudo bash scripts/deploy-aliyun-demo.sh"
