"""Unit tests for ingest chunk benchmarks (SPK-K02)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import Settings
from app.services.engagement_ingest_service import EngagementIngestService
from app.services.ingest.chunk_benchmarks import (
    TEMPLATE_QA_CHUNKS,
    TEMPLATE_RFQ_CHUNKS,
    TEMPLATE_TOTAL_CHUNKS,
    assert_template_chunk_benchmark,
    assert_vector_chunks_rfqa_only,
    summarize_doc_type_counts,
)

CORPUS = os.environ.get("ARIA_VALIDATION_CORPUS", r"E:/AI文档项目/RE_ 报价AI需求沟通")


def test_summarize_doc_type_counts():
    chunks = [
        {"metadata": {"doc_type": "rfq"}},
        {"metadata": {"doc_type": "rfq"}},
        {"metadata": {"doc_type": "qa"}},
    ]
    assert summarize_doc_type_counts(chunks) == {"rfq": 2, "qa": 1}


def test_assert_vector_chunks_rfqa_only_rejects_quote():
    with pytest.raises(ValueError, match="unexpected vector doc_type"):
        assert_vector_chunks_rfqa_only([{"metadata": {"doc_type": "quote_manpower"}}])


def test_assert_template_chunk_benchmark_accepts_expected_counts():
    chunks = [{"metadata": {"doc_type": "rfq"}}] * TEMPLATE_RFQ_CHUNKS
    chunks += [{"metadata": {"doc_type": "qa"}}] * TEMPLATE_QA_CHUNKS
    counts = assert_template_chunk_benchmark(chunks)
    assert counts == {"rfq": TEMPLATE_RFQ_CHUNKS, "qa": TEMPLATE_QA_CHUNKS}
    assert len(chunks) == TEMPLATE_TOTAL_CHUNKS


@pytest.mark.skipif(not Path(CORPUS).is_dir(), reason="validation corpus not on disk")
def test_validation_corpus_template_meets_171_benchmark():
    """SPK-K02: customer template must flatten to rfq 136 + qa 35."""
    kb_root = Path(CORPUS).parent
    engagement = Path(CORPUS)
    service = EngagementIngestService(
        Settings(
            knowledge_base_path=str(kb_root),
            mock_rag=False,
            manpower_baselines_path=str(engagement / "_baselines.json"),
        )
    )
    _manifest, chunks, _baseline = service.prepare_engagement(engagement)
    assert_template_chunk_benchmark(chunks)
