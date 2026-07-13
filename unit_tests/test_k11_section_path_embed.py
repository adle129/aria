"""Unit tests for RFQ section_path embed text (R1-K11)."""

from __future__ import annotations

from app.services.ingest.rfq_chunker import chunk_rfq_text
from app.services.knowledge_index_service import _chunk_content


def test_chunk_content_prepends_section_path():
    item = {
        "content": "P2阶段布置细节",
        "section_path": "四、工作内容及要求 > 4.1.1.1 P2",
        "metadata": {"section_path": "四、工作内容及要求 > 4.1.1.1 P2"},
    }
    text = _chunk_content(item)
    assert text.startswith("四、工作内容及要求 > 4.1.1.1 P2\n")
    assert "P2阶段布置细节" in text


def test_chunk_content_does_not_duplicate_path_prefix():
    body = "四、工作内容及要求 > 4.1\n已含路径的正文"
    item = {"content": body, "metadata": {"section_path": "四、工作内容及要求 > 4.1"}}
    assert _chunk_content(item) == body


def test_chunker_metadata_has_section_path_for_embed():
    text = "四、工作内容及要求\r总述\r4.1 工作内容\r细节\r"
    chunks = chunk_rfq_text(text, source_doc="t.doc")
    leaf = next(c for c in chunks if c["chunk_chapter"].startswith("4.1"))
    embedded = _chunk_content(leaf)
    assert leaf["section_path"] in embedded
    assert leaf["metadata"]["section_path"] == leaf["section_path"]
