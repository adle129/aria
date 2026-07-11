"""Unit tests for ingest chunk benchmarks (SPK-K02)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import Settings
from app.services.engagement_ingest_service import EngagementIngestService
from app.services.ingest.chunk_benchmarks import (
    SPIKE_RFQ_CHUNKS_MIN,
    TEMPLATE_QA_CHUNKS,
    TEMPLATE_RFQ_CHUNKS,
    TEMPLATE_TOTAL_CHUNKS,
    assert_template_chunk_benchmark,
    assert_vector_chunks_rfqa_only,
    summarize_doc_type_counts,
)

_DEFAULT_CORPUS = Path(r"E:/AI文档项目/RE_ 报价AI需求沟通")
_REPO_VALIDATION = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "data"
    / "knowledge_base"
    / "validation_template_engagement"
)


def _has_rfq_and_qa(folder: Path) -> bool:
    if not folder.is_dir():
        return False
    names = [p.name for p in folder.iterdir() if p.is_file()]
    has_rfq = any(
        "RFQ" in name.upper() and name.lower().endswith((".doc", ".docx")) for name in names
    )
    has_qa = any("Q_A" in name.upper() and name.lower().endswith(".xlsx") for name in names)
    return has_rfq and has_qa


def _resolve_validation_corpus() -> Path | None:
    """Prefer ARIA_VALIDATION_CORPUS, then local customer pack, then repo seed."""
    candidates: list[Path] = []
    env = os.environ.get("ARIA_VALIDATION_CORPUS")
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            _DEFAULT_CORPUS,
            _DEFAULT_CORPUS / "test",
            _REPO_VALIDATION,
        ]
    )
    for path in candidates:
        if _has_rfq_and_qa(path):
            return path.resolve()
    return None


CORPUS = _resolve_validation_corpus()


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


@pytest.mark.skipif(CORPUS is None, reason="validation corpus with RFQ+Q_A not on disk")
def test_validation_corpus_template_meets_171_benchmark():
    """SPK-K02: gold template flattens to rfq≥136 + qa=35 (index ≥171)."""
    engagement = CORPUS
    assert engagement is not None
    kb_root = engagement.parent
    service = EngagementIngestService(
        Settings(
            knowledge_base_path=str(kb_root),
            mock_rag=False,
            manpower_baselines_path=str(engagement / "_baselines.json"),
        )
    )
    _manifest, chunks, _baseline = service.prepare_engagement(engagement)
    counts = summarize_doc_type_counts(chunks)
    assert_vector_chunks_rfqa_only(chunks)
    assert counts.get("qa", 0) == TEMPLATE_QA_CHUNKS
    assert counts.get("rfq", 0) >= SPIKE_RFQ_CHUNKS_MIN
    assert sum(counts.get(k, 0) for k in ("rfq", "qa")) >= SPIKE_RFQ_CHUNKS_MIN + TEMPLATE_QA_CHUNKS
