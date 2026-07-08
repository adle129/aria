from pathlib import Path

import pytest

from app.config import Settings
from app.services.dimension_match_service import DimensionMatchService

SEED = Path(__file__).resolve().parents[1] / "backend" / "data" / "config" / "dimension_baseline.v1.json"


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
    chassis = next(i for i in draft["items"] if i["dimension_id"] == "chassis_front_susp")
    assert chassis["in_scope"] is True
    assert draft["module_summary"]


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


def test_match_invalid_llm_json_degrades(monkeypatch, match_service):
    rfq_modules = {"project_name": "test", "functions_in_scope": ["Chassis"]}

    class BadLLM:
        def complete_json(self, *_a, **_k):
            return {"parse_error": True, "raw_output": "not json"}

    match_service.settings = Settings(mock_llm=False, dimension_baseline_path=str(SEED))
    match_service.llm = BadLLM()
    draft = match_service.match_rfq_to_baseline(rfq_modules)
    assert len(draft["items"]) >= 20
