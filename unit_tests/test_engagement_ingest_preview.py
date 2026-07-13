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
    assert all("section_path" in c["metadata"] for c in chunks)


def test_chunk_rfq_section_path_hierarchy():
    text = (
        "四、工作内容及要求\r"
        "总述\r"
        "4.1 工作内容\r"
        "概述\r"
        "4.1.1 整车总布置开发\r"
        "布置说明\r"
        "4.1.1.1 P2阶段相应总布置工作\r"
        "P2细节\r"
        "4.1.1.2 P3阶段工作\r"
        "P3细节\r"
        "4.1.2 车身系统\r"
        "车身说明\r"
    )
    chunks = chunk_rfq_text(text, source_doc="scope.doc")
    by_chapter = {c["chunk_chapter"]: c for c in chunks}
    leaf = by_chapter["4.1.1.1 P2阶段相应总布置工作"]
    assert leaf["section_depth"] == 4
    assert "四、工作内容及要求" in leaf["section_path"]
    assert "4.1 工作内容" in leaf["section_path"]
    assert "4.1.1 整车总布置开发" in leaf["section_path"]
    assert leaf["section_path"].endswith("4.1.1.1 P2阶段相应总布置工作")
    sibling = by_chapter["4.1.2 车身系统"]
    assert "4.1.1" not in sibling["section_path"]
    assert "4.1 工作内容" in sibling["section_path"]


def test_chunk_rfq_dotted_heading_without_space_before_body():
    """Customer RFQ often writes '8.3对甲方…' without space after the number."""
    text = (
        "八、其他\r"
        "8.1 第一条建议。\r"
        "8.2 在更好地保证产品质量、降低成本的基础上，乙方可以不局限于甲方提出的技术要求。\r"
        "8.3对甲方提供的图纸、数模、技术资料等相关文件，乙方必须严格保密。\r"
        "8.4 其它约定。\r"
    )
    chunks = chunk_rfq_text(text, source_doc="RFQ_客户B.doc")
    chapters = [c["chunk_chapter"] for c in chunks]
    assert any(ch.startswith("8.2") for ch in chapters)
    assert any(ch.startswith("8.3") for ch in chapters)
    c82 = next(c for c in chunks if c["chunk_chapter"].startswith("8.2"))
    c83 = next(c for c in chunks if c["chunk_chapter"].startswith("8.3"))
    assert "8.3" not in c82["content"]
    assert "严格保密" in c83["content"]
    assert "八、其他" in c83["section_path"]


def test_chunk_rfq_arabic_dunhao_major_headings_from_docx_export():
    """LibreOffice/python-docx often emits '1、车型简介' instead of '一、车型简介'."""
    cover = ("封面\x07" * 30) + "\r"
    text = (
        cover
        + "目录\r一     车型简介\r二     工程联系\r三     项目要求\r"
        + "依据《合同法》委托设计如下：\r"
        + "1、车型简介\r"
        + "1.1 A级SUV新能源车型。\r"
        + "1.5 整车关键系统定义：\r"
        + "2、工程联系\r"
        + "2.1 甲方联系人\r"
        + "3、项目要求\r"
        + "3.1 项目总体要求\r"
    )
    chunks = chunk_rfq_text(text, source_doc="RFQ_模板.docx")
    by_chapter = {c["chunk_chapter"]: c for c in chunks}
    preamble = by_chapter["前言/目录"]["content"]
    assert "1、车型简介" not in preamble
    assert "1.1 A级SUV" not in preamble
    assert "2、工程联系" not in preamble
    vehicle = by_chapter.get("1、车型简介") or by_chapter.get("车型简介")
    assert vehicle is not None
    assert vehicle["chunk_chapter"].startswith(("1、", "一、")) or vehicle["chunk_chapter"] == "车型简介"
    assert "1.1 A级SUV" in vehicle["content"]
    contact = by_chapter.get("2、工程联系") or by_chapter.get("工程联系")
    assert contact is not None
    assert "2.1" in contact["content"]
    req = next(c for c in chunks if c["chunk_chapter"].startswith("3.1"))
    assert "3、项目要求" in req["section_path"] or "三、项目要求" in req["section_path"]


def test_chunk_rfq_indented_major_heading_not_swallowed_by_preamble():
    """Word often indents '一、车型简介'; must not stay inside 前言/目录."""
    cover = ("封面表格\x07单元格\x07" * 20) + "\r"
    text = (
        cover
        + "目录\r一     车型简介\r二     工程联系\r三     项目要求\r"
        + "依据《合同法》委托设计如下：\r"
        + "  一、车型简介\r"
        + "1.1 A级SUV新能源车型。\r"
        + "1.5 整车关键系统定义：\r"
        + "  二、工程联系\r"
        + "2.1 甲方联系人\r"
        + "三、项目要求\r"
        + "3.1 项目总体要求\r"
    )
    chunks = chunk_rfq_text(text, source_doc="RFQ_模板.docx")
    by_chapter = {c["chunk_chapter"]: c for c in chunks}
    assert "前言/目录" in by_chapter
    preamble = by_chapter["前言/目录"]["content"]
    assert "一、车型简介" not in preamble
    assert "1.1 A级SUV" not in preamble
    vehicle = by_chapter.get("一、车型简介") or by_chapter.get("车型简介")
    assert vehicle is not None
    assert "1.1 A级SUV" in vehicle["content"]
    assert "1.5 整车关键系统定义" in vehicle["content"]
    leaf = next(c for c in chunks if c["chunk_chapter"].startswith("3.1"))
    assert "三、项目要求" in leaf["section_path"]


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
    assert any(ch.startswith("三、") or ch.startswith("3.") for ch in chapters)
    vehicle = next(c for c in chunks if c["chunk_chapter"] == "车型简介")
    assert "A级SUV" in vehicle["content"]
    contact = next(c for c in chunks if c["chunk_chapter"] == "工程联系")
    assert "2.1" in contact["content"]
    leaf = next(c for c in chunks if c["chunk_chapter"].startswith("3.1"))
    assert "三、项目要求" in leaf["section_path"]


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
    vehicle = next(c for c in chunks if "车型简介" in c["chunk_chapter"])
    assert vehicle["chunk_chapter"] in {"一、车型简介", "车型简介"}
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
