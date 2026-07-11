"""Unit tests for retrieval evaluation (R1-K09)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import Settings
from app.services.kb_eval_service import (
    SPIKE_VECTOR_PASS_MIN,
    SPIKE_VECTOR_PASS_TOTAL,
    eval_retrieval_hit,
    run_production_retrieval_eval,
    run_retrieval_eval,
)

SAMPLE_QUERIES = Path(__file__).resolve().parents[1] / "backend" / "data" / "debug_eval_queries.sample.json"
SPIKE_REPORT = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "data"
    / "validation_reports"
    / "rag_compare_spike.json"
)


def test_eval_retrieval_hit_by_expected_area():
    item = {"expected_area": "GD&T"}
    hits = [{"metadata": {"area": "GD&T"}, "similarity_score": 0.7}]
    assert eval_retrieval_hit(item, hits) is True


def test_eval_retrieval_hit_fails_when_no_hits():
    assert eval_retrieval_hit({"expected_area": "PM"}, []) is False


def test_run_retrieval_eval_counts_passes():
    queries = [
        {"query": "q1", "expected_area": "A"},
        {"query": "q2", "expected_area": "B"},
    ]

    def search(_query, *, top_k=3, doc_type_filter=None, function_filter=None):
        if _query == "q1":
            return [{"metadata": {"area": "A"}, "similarity_score": 0.8}]
        return [{"metadata": {"area": "X"}, "similarity_score": 0.8}]

    report = run_retrieval_eval(queries, search, top_k=3)
    assert report["total"] == 2
    assert report["passed"] == 1
    assert report["pass_rate"] == 0.5


def test_run_production_retrieval_eval_uses_rag_service(monkeypatch, tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    settings = Settings(mock_rag=False, knowledge_base_path=str(kb))

    class FakeIndex:
        def search(
            self,
            query,
            *,
            top_k=5,
            function_filter=None,
            doc_type_filter=None,
            request_type="query",
        ):
            return [{"metadata": {"area": "Packaging"}, "similarity_score": 0.9, "content": "x"}]

    monkeypatch.setattr(
        "app.services.knowledge_index_service.KnowledgeIndexService",
        lambda _settings, namespace=None: FakeIndex(),
    )
    queries = [{"query": "benchmark packaging", "expected_area": "Packaging"}]
    report = run_production_retrieval_eval(settings, queries, top_k=3)
    assert report["passed"] == 1


@pytest.mark.skipif(not SAMPLE_QUERIES.is_file(), reason="sample eval queries missing")
def test_sample_eval_queries_load():
    queries = json.loads(SAMPLE_QUERIES.read_text(encoding="utf-8"))
    assert len(queries) == SPIKE_VECTOR_PASS_TOTAL


@pytest.mark.skipif(not SPIKE_REPORT.is_file(), reason="spike report missing")
def test_spike_vector_pass_rate_contract():
    """Internal baseline: vector mode must stay >= 12/15 per spike closure."""
    report = json.loads(SPIKE_REPORT.read_text(encoding="utf-8"))
    vector = report["summary"]["vector"]
    assert vector["total"] == SPIKE_VECTOR_PASS_TOTAL
    assert vector["passed"] >= SPIKE_VECTOR_PASS_MIN
