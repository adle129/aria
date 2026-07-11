"""Ingest chunk count benchmarks (spike closure + current chunker)."""

from __future__ import annotations

from typing import Any

# Spike index (2026-07-06): rfq 136 + qa 35 = 171
SPIKE_RFQ_CHUNKS_MIN = 136
SPIKE_QA_CHUNKS = 35
SPIKE_TOTAL_CHUNKS_MIN = SPIKE_RFQ_CHUNKS_MIN + SPIKE_QA_CHUNKS

# Current production chunker on customer template (2026-07-07)
TEMPLATE_RFQ_CHUNKS = 142
TEMPLATE_QA_CHUNKS = SPIKE_QA_CHUNKS
TEMPLATE_TOTAL_CHUNKS = TEMPLATE_RFQ_CHUNKS + TEMPLATE_QA_CHUNKS

_VECTOR_DOC_TYPES = frozenset({"rfq", "qa"})


def summarize_doc_type_counts(chunks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for chunk in chunks:
        doc_type = str((chunk.get("metadata") or {}).get("doc_type") or "unknown")
        counts[doc_type] = counts.get(doc_type, 0) + 1
    return counts


def assert_vector_chunks_rfqa_only(chunks: list[dict[str, Any]]) -> None:
    for chunk in chunks:
        doc_type = (chunk.get("metadata") or {}).get("doc_type")
        if doc_type not in _VECTOR_DOC_TYPES:
            raise ValueError(f"unexpected vector doc_type: {doc_type!r}")


def assert_template_chunk_benchmark(
    chunks: list[dict[str, Any]],
    *,
    rfq: int = TEMPLATE_RFQ_CHUNKS,
    qa: int = TEMPLATE_QA_CHUNKS,
    rfq_min: int = SPIKE_RFQ_CHUNKS_MIN,
) -> dict[str, int]:
    """Assert template ingest benchmark; returns doc_type_counts."""
    counts = summarize_doc_type_counts(chunks)
    assert_vector_chunks_rfqa_only(chunks)
    rfq_count = counts.get("rfq", 0)
    if rfq_count < rfq_min:
        raise AssertionError(f"rfq chunks: expected >= {rfq_min}, got {rfq_count}")
    if counts.get("qa", 0) != qa:
        raise AssertionError(f"qa chunks: expected {qa}, got {counts.get('qa', 0)}")
    if rfq_count != rfq:
        raise AssertionError(f"rfq chunks: expected {rfq}, got {rfq_count}")
    if len(chunks) != rfq + qa:
        raise AssertionError(f"total chunks: expected {rfq + qa}, got {len(chunks)}")
    return counts
