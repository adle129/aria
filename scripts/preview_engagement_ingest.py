#!/usr/bin/env python3
"""Preview R1 engagement ingest: RFQ chunks, Q_A rows, quote baselines.

Default corpus: E:/AI文档项目/RE_ 报价AI需求沟通
Override: ARIA_VALIDATION_CORPUS=<folder>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DEFAULT_CORPUS = Path(r"E:/AI文档项目/RE_ 报价AI需求沟通")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview engagement ingest / chunking")
    parser.add_argument(
        "corpus_dir",
        nargs="?",
        default=os.environ.get("ARIA_VALIDATION_CORPUS", str(DEFAULT_CORPUS)),
        help="Folder with RFQ + Q_A + 报价 Excel templates",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "backend" / "data" / "validation_reports" / "engagement_preview.json",
        help="Write JSON report path",
    )
    args = parser.parse_args()
    corpus = Path(args.corpus_dir)
    if not corpus.is_dir():
        print(f"ERROR: corpus not found: {corpus}", file=sys.stderr)
        return 1

    from app.services.ingest.engagement_preview import build_engagement_preview

    report = build_engagement_preview(corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    s = report["summary"]
    print(f"Corpus: {corpus}")
    print(f"RFQ chunks: {s.get('rfq_chunks')} | Q_A rows: {s.get('qa_row_chunks')} | Quote functions: {s.get('quote_functions')}")
    if report["errors"]:
        print("Errors:", report["errors"])
    print(f"Report: {args.output}")
    return 0 if not report["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
