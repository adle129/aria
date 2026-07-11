from pathlib import Path

import pytest

from app.services.llm_service import LLMService
from app.services.rfq_parser import RFQParser
from app.config import Settings

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


def test_extract_text_from_sample_docx():
    parser = RFQParser()
    text = parser.extract_text_from_docx(SAMPLE_RFQ)
    assert "Mock Auto" in text
    assert "Chassis" in text


def test_extract_rfq_text_from_sample_docx():
    parser = RFQParser()
    text = parser.extract_rfq_text(SAMPLE_RFQ)
    assert "Mock Auto" in text
    assert "Chassis" in text


def test_extract_missing_file_raises():
    parser = RFQParser()
    with pytest.raises(FileNotFoundError):
        parser.extract_text_from_docx("missing.docx")


def test_mock_llm_returns_structured_json():
    parser = RFQParser()
    rfq_text = parser.extract_text_from_docx(SAMPLE_RFQ)
    llm = LLMService(Settings(mock_llm=True))
    result = llm.complete_json("ignored", rfq_text=rfq_text)
    assert result["platform_type"] == "MEB"
    assert "Chassis" in result["functions_in_scope"]
    assert result.get("new_project_profile")
