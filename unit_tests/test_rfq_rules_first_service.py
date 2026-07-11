"""Unit tests for production rules-first parse service (SPK-F04/F07)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.services.rfq_rules_first_service import parse_rfq_modules, run_parse_report

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"

_FAKE_RULES = {
    "project_name": "Demo Project",
    "customer": "ACME",
    "platform_type": "MEB",
    "functions_in_scope": ["Chassis", "PM"],
    "development_scope": [{"id": "4.1.1", "title": "底盘", "function": "Chassis"}],
    "modules": [{"function": "Chassis", "module_name": "Suspension", "deliverables": ["M1 data"]}],
    "milestones": {"P1": "2026-06-01"},
    "special_requirements": [],
    "timeline_months": 18,
    "_rules_stats": {"milestones_count": 1, "modules_count": 1, "development_scope_count": 1, "deliverable_sections": 0},
}


@pytest.fixture
def rules_only_parse(monkeypatch):
    monkeypatch.setattr("app.services.rfq_rules_first_service.load_rfq_text", lambda _p: ("rfq text", "docx"))
    monkeypatch.setattr("app.services.rfq_rules_first_service.chunk_rfq_text", lambda _t, **_: [{"chunk_chapter": "body", "content": "x"}])
    monkeypatch.setattr("app.services.rfq_rules_first_service.extract_rfq_rules", lambda _t, _c: dict(_FAKE_RULES))
    monkeypatch.setattr("app.services.rfq_rules_first_service.needs_overview_llm", lambda _r: False)
    monkeypatch.setattr("app.services.rfq_rules_first_service.needs_scope_llm", lambda _r, **_: False)

    class RulesOnlyLLM:
        def complete_json(self, *_a, **_k):
            raise AssertionError("LLM should not be called when rules sufficient")

    monkeypatch.setattr("app.services.rfq_rules_first_service.LLMService", lambda _s: RulesOnlyLLM())


def test_parse_rfq_modules_rules_only_no_llm(rules_only_parse):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    result = parse_rfq_modules(Settings(mock_llm=False), SAMPLE_RFQ)
    assert result["project_name"] == "Demo Project"
    assert result["milestones"]["P1"] == "2026-06-01"
    assert len(result["modules"]) == 1


def test_run_parse_report_includes_validation(rules_only_parse):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    report = run_parse_report(Settings(mock_llm=False), rfq_path=SAMPLE_RFQ)
    assert report["parse_strategy"] == "rules_first"
    assert report["validation"]["ok"] is True
    assert report["result"]["project_name"] == "Demo Project"


def test_run_parse_report_llm_fallback_on_scope_gap(monkeypatch):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    sparse_rules = dict(_FAKE_RULES)
    sparse_rules["modules"] = []
    sparse_rules["_rules_stats"] = {"milestones_count": 1, "modules_count": 0, "development_scope_count": 0, "deliverable_sections": 0}
    monkeypatch.setattr("app.services.rfq_rules_first_service.load_rfq_text", lambda _p: ("rfq text", "docx"))
    monkeypatch.setattr(
        "app.services.rfq_rules_first_service.chunk_rfq_text",
        lambda _t, **_: [{"chunk_chapter": "4.2.1 GI", "content": "4.2.1 table"}],
    )
    monkeypatch.setattr("app.services.rfq_rules_first_service.extract_rfq_rules", lambda _t, _c: dict(sparse_rules))
    monkeypatch.setattr("app.services.rfq_rules_first_service.needs_overview_llm", lambda _r: False)
    monkeypatch.setattr("app.services.rfq_rules_first_service.needs_scope_llm", lambda _r, **_: True)
    monkeypatch.setattr(
        "app.services.rfq_rules_first_service.LLMService",
        lambda _s: MagicMock(
            complete_json=MagicMock(
                return_value={
                    "modules": [{"function": "GI", "module_name": "Package", "deliverables": []}],
                    "development_scope": [{"id": "4.1.1", "title": "GI", "function": "GI"}],
                }
            )
        ),
    )
    report = run_parse_report(Settings(mock_llm=False), rfq_path=SAMPLE_RFQ)
    assert report["llm_batches"] >= 1
    assert len(report["result"]["modules"]) >= 1
