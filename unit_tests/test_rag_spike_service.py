"""Unit tests for RAG spike compare (no Ollama / PostgreSQL)."""

from __future__ import annotations

from app.services.rag_spike_service import (
    eval_hit,
    keyword_overlap_score,
    reciprocal_rank_fusion,
    rerank_lite,
    tokenize_query,
)


def test_tokenize_query_mixed():
    terms = tokenize_query("物理对标 benchmark 报告")
    assert "benchmark" in terms
    assert "物理对标" in terms or "报告" in terms


def test_keyword_overlap_score():
    hit = {
        "content": "物理对标 benchmark 报告 for packaging",
        "metadata": {"area": "Packaging", "source_doc": "Q_A.xlsx"},
    }
    score = keyword_overlap_score("benchmark Packaging", hit)
    assert score > 0.5


def test_reciprocal_rank_fusion():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "d"]])
    assert fused["b"] > fused["a"]
    assert fused["b"] > fused["d"]


def test_rerank_lite_orders_by_combined_score():
    hits = [
        {"chunk_id": "1", "content": "alpha", "metadata": {}, "similarity_score": 0.9},
        {"chunk_id": "2", "content": "benchmark packaging", "metadata": {"area": "Packaging"}, "similarity_score": 0.5},
    ]
    reranked = rerank_lite("benchmark Packaging", hits)
    assert reranked[0]["chunk_id"] == "2"


def test_eval_hit_expected_area():
    item = {"query": "x", "expected_area": "GD&T"}
    hits = [{"metadata": {"area": "GD&T"}, "similarity_score": 0.4}]
    assert eval_hit(item, hits) is True


def test_eval_hit_min_score():
    item = {"query": "x", "min_score": 0.3}
    hits = [{"metadata": {}, "similarity_score": 0.35}]
    assert eval_hit(item, hits) is True
