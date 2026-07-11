import json

import pytest

from app.utils.json_utils import extract_json_from_text, normalize_llm_json, safe_parse_llm_json


def test_extract_json_from_fenced_block():
    raw = 'prefix\n```json\n{"a": 1}\n```\nsuffix'
    assert extract_json_from_text(raw) == {"a": 1}


def test_safe_parse_invalid_json_returns_raw():
    result = safe_parse_llm_json("not-json")
    assert result["parse_error"] is True
    assert "not-json" in result["raw_output"]


def test_normalize_list_of_modules():
    data = [{"function": "Chassis", "module_name": "Front suspension", "description": "x"}]
    assert normalize_llm_json(data)["modules"] == data


def test_safe_parse_list_json():
    raw = '[{"function": "CAE", "module_name": "NVH", "description": "分析"}]'
    result = safe_parse_llm_json(raw)
    assert not result.get("parse_error")
    assert len(result["modules"]) == 1
