from pathlib import Path

import pytest

from app.config import Settings
from app.services.dimension_match_service import (
    DimensionMatchService,
    _looks_like_structured_dump,
    _rfq_corpus_raw,
    _rfq_text_parts,
    compute_review_tier,
    infer_match_meta_from_legacy,
)

SEED = Path(__file__).resolve().parents[1] / "backend" / "data" / "config" / "dimension_baseline.v1.json"

BIW_RFQ_FIXTURE = {
    "project_name": "MEB BIW RFQ",
    "functions_in_scope": ["BIW", "Chassis"],
    "development_scope": [
        {"id": "4.1.2", "title": "车身系统开发", "function": "BIW", "content": "白车身 BIW 结构设计与验证"},
        {"id": "4.1.3", "title": "底盘系统开发", "function": "Chassis"},
    ],
    "modules": [{"function": "BIW", "module_name": "白车身结构", "deliverables": []}],
}


def assert_customer_readable_keyword_evidence(item: dict) -> None:
    """F1.10c drawer/table must not expose internal corpus or search jargon."""
    assert item.get("match_type") == "keywords"
    source_ref = str(item.get("source_ref") or "")
    evidence = item.get("evidence") or {}
    snippet = str(evidence.get("snippet") or "")
    assert "命中" not in source_ref, source_ref
    assert not _looks_like_structured_dump(snippet), snippet
    assert "{" not in snippet, snippet
    assert evidence.get("matched_keyword"), item.get("dimension_id")


@pytest.fixture
def match_service():
    if not SEED.is_file():
        pytest.skip("seed baseline missing")
    return DimensionMatchService(
        Settings(mock_llm=True, dimension_baseline_path=str(SEED))
    )


def test_match_rfq_keywords_prefill_chassis(match_service):
    rfq_modules = {
        "project_name": "MEB Chassis RFQ",
        "functions_in_scope": ["Chassis", "PM"],
        "modules": [
            {
                "function": "Chassis",
                "module_name": "Front suspension MacPherson layout",
                "deliverables": ["Suspension CAD"],
            }
        ],
    }
    draft = match_service.match_rfq_to_baseline(rfq_modules)
    assert draft["baseline_version"] == "v1"
    assert len(draft["items"]) >= 20
    assert draft["review_summary"]["total"] == len(draft["items"])
    chassis = next(i for i in draft["items"] if i["dimension_id"] == "chassis_front_susp")
    assert chassis["in_scope"] is True
    assert chassis["match_type"] == "keywords"
    assert chassis["review_tier"] == "auto_include"
    assert chassis["source_label"] == "关键词匹配"
    assert chassis["evidence"].get("matched_keyword")
    assert_customer_readable_keyword_evidence(chassis)
    assert draft["module_summary"]


def test_match_module_scope_defaults_unchecked(match_service):
    rfq_modules = {
        "project_name": "Chassis program",
        "functions_in_scope": ["Chassis"],
        "modules": [{"function": "Chassis", "module_name": "General chassis", "deliverables": []}],
    }
    draft = match_service.match_rfq_to_baseline(rfq_modules)
    risk = next(i for i in draft["items"] if i["dimension_id"] == "pm_risk_change")
    assert risk["in_scope"] is False
    assert risk["match_type"] == "none" or risk["review_tier"] == "auto_exclude"


def test_chassis_module_scope_item_needs_review(match_service):
    rfq_modules = {
        "project_name": "Chassis",
        "functions_in_scope": ["Chassis"],
        "modules": [{"function": "Chassis", "module_name": "Rear axle", "deliverables": []}],
    }
    draft = match_service.match_rfq_to_baseline(rfq_modules)
    rear = next(i for i in draft["items"] if i["dimension_id"] == "chassis_rear_susp")
    if rear["match_type"] == "module_scope":
        assert rear["review_tier"] == "needs_review"
        assert rear["in_scope"] is False
        assert rear["source_label"] == "模块范围推断"


def test_match_rfq_out_of_scope_gets_dash(match_service):
    rfq_modules = {
        "project_name": "Interior only",
        "functions_in_scope": ["Interior"],
        "modules": [{"function": "Interior", "module_name": "IP trim", "deliverables": []}],
    }
    draft = match_service.match_rfq_to_baseline(rfq_modules)
    chassis = next(i for i in draft["items"] if i["dimension_id"] == "chassis_front_susp")
    assert chassis["in_scope"] is False
    assert chassis["work_content"] == "—"
    assert chassis["review_tier"] == "auto_exclude"


def test_compute_review_tier_legacy_module_scope():
    item = {"source_ref": "module_scope", "in_scope": True}
    meta = infer_match_meta_from_legacy(item)
    assert meta["match_type"] == "module_scope"
    assert compute_review_tier(meta) == "needs_review"


def test_match_rfq_biw_keyword_uses_readable_scope_evidence(match_service):
    draft = match_service.match_rfq_to_baseline(BIW_RFQ_FIXTURE)
    biw = next(i for i in draft["items"] if i["dimension_id"] == "biw_body_structure")
    assert biw["match_type"] == "keywords"
    assert biw["evidence"]["rfq_section"] == "4.1.2"
    assert biw["evidence"]["rfq_section_title"] == "车身系统开发"
    assert biw["evidence"]["snippet"] == "白车身 BIW 结构设计与验证"
    assert biw["source_ref"] == "RFQ §4.1.2 · 车身系统开发"
    assert_customer_readable_keyword_evidence(biw)


def test_all_keyword_matches_customer_readable(match_service):
    draft = match_service.match_rfq_to_baseline(BIW_RFQ_FIXTURE)
    keyword_items = [i for i in draft["items"] if i.get("match_type") == "keywords"]
    assert keyword_items, "fixture should produce keyword matches"
    for item in keyword_items:
        assert_customer_readable_keyword_evidence(item)


def test_development_scope_list_not_stringified_in_corpus():
    parts = _rfq_text_parts(BIW_RFQ_FIXTURE)
    joined = "\n".join(parts)
    assert "[{'id':" not in joined
    assert "车身系统开发" in joined
    assert "白车身 BIW 结构设计与验证" in joined


def test_rfq_corpus_raw_excludes_python_dict_repr():
    corpus = _rfq_corpus_raw(BIW_RFQ_FIXTURE)
    assert _looks_like_structured_dump(corpus) is False
    assert "function" not in corpus or "BIW" in corpus


def test_looks_like_structured_dump_detects_legacy_snippets():
    assert _looks_like_structured_dump("[{'id': '4.1.2', 'title': '车身'}]") is True
    assert _looks_like_structured_dump("车身系统开发（含 BIW）") is False
    assert _looks_like_structured_dump("…前悬架 MacPherson 布置…") is False


def test_match_invalid_llm_json_degrades(monkeypatch, match_service):
    rfq_modules = {"project_name": "test", "functions_in_scope": ["Chassis"]}

    class BadLLM:
        def complete_json(self, *_a, **_k):
            return {"parse_error": True, "raw_output": "not json"}

    match_service.settings = Settings(mock_llm=False, dimension_baseline_path=str(SEED))
    match_service.llm = BadLLM()
    draft = match_service.match_rfq_to_baseline(rfq_modules)
    assert len(draft["items"]) >= 20
    assert "review_summary" in draft


def test_match_rfq_reports_llm_batch_progress(match_service, monkeypatch):
    calls: list[tuple[int, int]] = []

    def fake_llm_batch(_rfq_modules, batch, **_kwargs):
        return []

    monkeypatch.setattr(match_service, "_llm_batch", fake_llm_batch)
    match_service.settings = Settings(mock_llm=False, dimension_baseline_path=str(SEED))

    draft = match_service.match_rfq_to_baseline(
        BIW_RFQ_FIXTURE,
        on_progress=lambda done, total: calls.append((done, total)),
    )
    assert len(draft["items"]) >= 1
    assert calls
    assert calls[0] == (1, len(calls))
    assert calls[-1][0] == calls[-1][1]
