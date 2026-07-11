#!/usr/bin/env bash
set -euo pipefail

docker exec aria-backend python scripts/ingest_documents.py
echo "Re-index completed (full ingest via ingest_documents.py)."
