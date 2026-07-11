"""Unit tests for RFQParseService (R1-F04)."""

from pathlib import Path

import pytest

from app.config import Settings
from app.services.rfq_parse_service import RFQParseService

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


@pytest.fixture
def parse_service():
    return RFQParseService(Settings(mock_llm=True))


def test_parse_rules_first_mock_returns_modules(parse_service):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    result = parse_service.parse_rules_first(SAMPLE_RFQ)
    assert isinstance(result, dict)
    assert result.get("project_name") or result.get("functions_in_scope")


def test_parse_rules_first_missing_file(parse_service):
    with pytest.raises(FileNotFoundError):
        parse_service.parse_rules_first("/nonexistent/rfq.docx")


def test_parse_rules_first_production_delegates_to_spike(monkeypatch, tmp_path):
    rfq = tmp_path / "rfq.docx"
    rfq.touch()
    captured: dict = {}

    def fake_parse(_settings, path, **_kwargs):
        captured["path"] = path
        return {"project_name": "Spike Project", "functions_in_scope": ["PM"]}

    monkeypatch.setattr(
        "app.services.rfq_rules_first_service.parse_rfq_modules",
        fake_parse,
    )
    svc = RFQParseService(Settings(mock_llm=False))
    result = svc.parse_rules_first(rfq)
    assert result["project_name"] == "Spike Project"
    assert captured["path"] == rfq


def test_parse_rules_first_production_invalid_report_raises(monkeypatch, tmp_path):
    rfq = tmp_path / "rfq.docx"
    rfq.touch()

    def bad(*_a, **_k):
        raise ValueError("rules_first parse did not return rfq_modules dict")

    monkeypatch.setattr("app.services.rfq_rules_first_service.parse_rfq_modules", bad)
    svc = RFQParseService(Settings(mock_llm=False))
    with pytest.raises(ValueError, match="rfq_modules"):
        svc.parse_rules_first(rfq)
