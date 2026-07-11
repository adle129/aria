"""Unit tests for engagement ingest preview (optional local corpus)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services.ingest.qa_row_loader import load_qa_rows
from app.services.ingest.rfq_chunker import chunk_rfq_text

SAMPLES_QA = Path(__file__).resolve().parents[1] / "backend" / "data" / "templates" / "qa_template.xlsx"
CORPUS = os.environ.get("ARIA_VALIDATION_CORPUS", r"E:/AI文档项目/RE_ 报价AI需求沟通")


def test_chunk_rfq_text_splits_sections():
    text = "前言\r一、车型简介\r内容A\r二、项目要求\r内容B\r3.1 细则\r内容C"
    chunks = chunk_rfq_text(text, source_doc="t.doc")
    assert len(chunks) >= 2
    assert all(c["chunk_id"] and c["metadata"]["doc_type"] == "rfq" for c in chunks)


def test_chunk_rfq_bare_toc_titles_in_body():
    """Customer .doc: TOC uses spaces; body omits 一、/二、 but keeps 三、."""
    text = (
        "封面\r目录\r一     车型简介\r二     工程联系\r三     项目要求\r"
        "依据合同法...\r"
        "车型简介\r"
        "A级SUV新能源车型。\r"
        "工程联系\r"
        "2.1 甲方联系人...\r"
        "三、项目要求\r"
        "3.1 项目总体要求\r"
        "细则内容\r"
    )
    chunks = chunk_rfq_text(text, source_doc="RFQ.doc")
    chapters = [c["chunk_chapter"] for c in chunks]
    assert "车型简介" in chapters
    assert "工程联系" in chapters
    assert any("三、" in ch or ch.startswith("3.") for ch in chapters)
    vehicle = next(c for c in chunks if c["chunk_chapter"] == "车型简介")
    assert "A级SUV" in vehicle["content"]
    contact = next(c for c in chunks if c["chunk_chapter"] == "工程联系")
    assert "2.1" in contact["content"]


def test_chunk_rfq_cn_prefixed_body_with_numbered_clauses():
    text = (
        "目录\r一     车型简介\r"
        "依据...\r"
        "一、车型简介\r"
        "1.1 first item\r"
        "1.4 tire size\r"
        "R19\r"
        "1.5 key systems:\r"
        "[TABLE] Item | Value\r"
        "二、工程联系\r"
        "2.1 contacts\r"
    )
    chunks = chunk_rfq_text(text, source_doc="RFQ.doc")
    vehicle = next(c for c in chunks if c["chunk_chapter"] == "车型简介")
    assert "1.1 first item" in vehicle["content"]
    assert "1.4 tire size" in vehicle["content"]
    assert "1.5 key systems" in vehicle["content"]
    assert "[TABLE]" in vehicle["content"]


def test_load_qa_rows_from_demo_template_if_present():
    if not SAMPLES_QA.exists():
        pytest.skip("qa_template.xlsx not in repo")
    rows = load_qa_rows(SAMPLES_QA)
    assert len(rows) >= 1
    assert rows[0]["metadata"]["doc_type"] == "qa"


@pytest.mark.skipif(not Path(CORPUS).is_dir(), reason="validation corpus not on disk")
def test_build_engagement_preview_on_customer_corpus():
    from app.services.ingest.engagement_preview import build_engagement_preview

    report = build_engagement_preview(Path(CORPUS))
    assert report["summary"]["errors"] == 0 or report["rfq"] or report["qa"]
    if report["rfq"]:
        assert report["rfq"]["chunk_count"] >= 3
    if report["qa"]:
        assert report["qa"]["row_chunks"] >= 3
