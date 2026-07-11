from typing import Any

from app.services.retrieval_eval_service import evaluate_retrieval_queries


def test_eval_passes_on_area_match():
    queries = [{"query": "数据管理", "expected_area": "Data Management"}]
    report = evaluate_retrieval_queries(
        lambda q, dt: [{"similarity_score": 0.8, "metadata": {"area": "Data Management"}}],
        queries,
    )
    assert report["passed"] == 1
    assert report["pass_rate"] == 1.0


def test_eval_fails_without_hits():
    report = evaluate_retrieval_queries(lambda q, dt: [], [{"query": "missing", "expected_area": "X"}])
    assert report["passed"] == 0


def test_eval_respects_doc_type_filter_callback():
    seen: list[list[str] | None] = []

    def search(q: str, doc_types: list[str] | None) -> list[dict[str, Any]]:
        seen.append(doc_types)
        return [{"similarity_score": 0.9, "metadata": {"area": "Chassis"}}]

    evaluate_retrieval_queries(
        search,
        [{"query": "硬点", "expected_doc_types": ["qa"], "expected_area": "Chassis"}],
    )
    assert seen == [["qa"]]
