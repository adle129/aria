#!/usr/bin/env python3
"""Seed R1-internal engagement(s) under knowledge_base/ (no customer data required).

Creates dev_template_engagement with RFQ sample + synthetic Q_A rows so ingest
passes rfq+qa gate. If ARIA_VALIDATION_CORPUS exists, also copies customer
*template* files (unsigned templates — not customer project data).

Usage:
  python scripts/seed_internal_engagement.py
  python scripts/seed_internal_engagement.py --force
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

DEFAULT_CORPUS = Path(r"E:/AI文档项目/RE_ 报价AI需求沟通")
ENGAGEMENT_ID = "dev_template_engagement"
CORPUS_ENGAGEMENT_ID = "validation_template_engagement"

DEV_QA_ROWS = [
    ("1", "Packaging", "Who will do the physical benchmark?"),
    ("2", "GD&T", "General tolerance, parts tolerance, mounting concept"),
    ("3", "Data Management", "如何定义数据管理的方式？数据传输方式？"),
    ("4", "Change Management", "谁负责设计变更，M2之前？M2之后？"),
    ("5", "BE", "对于骡子车，用什么样的Donar car做基础？"),
    ("6", "Chassis", "是否需要我司进行硬点分析调整"),
    ("7", "PM", "Confirm complete project development timing plan"),
    ("8", "CAE", "CAE simulation scope for chassis load cases"),
]


def _write_minimal_qa_xlsx(path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Q_A"
    headers = [
        "No",
        "Area",
        "Author",
        "Question",
        "Assumption 我司",
        "Answer by customer",
        "Impact",
        "History Reference",
    ]
    ws.append(headers)
    for no, area, question in DEV_QA_ROWS:
        ws.append([no, area, "EDAG", question, "", "", "Technical", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _seed_dev_engagement(kb_root: Path, *, force: bool) -> Path:
    folder = kb_root / ENGAGEMENT_ID
    if folder.exists() and not force:
        print(f"[skip] {folder} exists (use --force)")
        return folder
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

    rfq_src = ROOT / "samples" / "rfq" / "mock_chassis_rfq.docx"
    if not rfq_src.is_file():
        raise FileNotFoundError(f"Missing sample RFQ: {rfq_src}")
    shutil.copy2(rfq_src, folder / "RFQ_mock.docx")
    _write_minimal_qa_xlsx(folder / "Q_A_dev.xlsx")

    manifest = {
        "engagement_id": ENGAGEMENT_ID,
        "project_name": "Dev Template Engagement (internal)",
        "customer": "Internal",
        "year": 2026,
        "functions": ["Chassis", "PM", "CAE"],
        "documents": [
            {"path": "RFQ_mock.docx", "doc_type": "rfq"},
            {"path": "Q_A_dev.xlsx", "doc_type": "qa"},
        ],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] seeded {folder}")
    return folder


def _seed_corpus_engagement(kb_root: Path, corpus: Path, *, force: bool) -> Path | None:
    if not corpus.is_dir():
        print(f"[skip] validation corpus not found: {corpus}")
        return None

    folder = kb_root / CORPUS_ENGAGEMENT_ID
    if folder.exists() and not force:
        print(f"[skip] {folder} exists (use --force)")
        return folder
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

    copied: list[dict[str, str]] = []
    mapping = [
        ("RFQ_模板.doc", "RFQ_template.doc", "rfq"),
        ("RFQ_模板.docx", "RFQ_template.docx", "rfq"),
        ("Q_A_模板.xlsx", "Q_A_template.xlsx", "qa"),
        ("报价人力模板.xlsx", "Quote_template.xlsx", "quote_manpower"),
    ]
    for src_name, dst_name, doc_type in mapping:
        if _copy_if_exists(corpus / src_name, folder / dst_name):
            copied.append({"path": dst_name, "doc_type": doc_type})

    if not any(d["doc_type"] == "rfq" for d in copied):
        print("[skip] corpus engagement: no RFQ template file found")
        shutil.rmtree(folder)
        return None
    if not any(d["doc_type"] == "qa" for d in copied):
        print("[warn] corpus engagement: no Q_A template — adding synthetic Q_A")
        _write_minimal_qa_xlsx(folder / "Q_A_dev.xlsx")
        copied.append({"path": "Q_A_dev.xlsx", "doc_type": "qa"})

    manifest = {
        "engagement_id": CORPUS_ENGAGEMENT_ID,
        "project_name": "Customer Template Corpus (internal validation)",
        "customer": "Template",
        "year": 2026,
        "functions": ["Chassis", "PM", "BIW", "CAE", "EE"],
        "documents": copied,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] seeded corpus engagement {folder} ({len(copied)} docs)")
    return folder


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed internal R1 knowledge_base engagements")
    parser.add_argument(
        "--knowledge-base",
        default=str(BACKEND / "data" / "knowledge_base"),
        help="knowledge_base root",
    )
    parser.add_argument("--corpus", default=os.environ.get("ARIA_VALIDATION_CORPUS", str(DEFAULT_CORPUS)))
    parser.add_argument("--force", action="store_true", help="Overwrite existing seed folders")
    parser.add_argument("--skip-corpus", action="store_true", help="Only seed dev_template_engagement")
    args = parser.parse_args()

    kb_root = Path(args.knowledge_base)
    kb_root.mkdir(parents=True, exist_ok=True)
    _seed_dev_engagement(kb_root, force=args.force)
    if not args.skip_corpus:
        _seed_corpus_engagement(kb_root, Path(args.corpus), force=args.force)
    print(f"[done] knowledge_base ready under {kb_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
