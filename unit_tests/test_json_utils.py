import json

import pytest

from app.utils.json_utils import extract_json_from_text, safe_parse_llm_json


def test_extract_json_from_fenced_block():
    raw = 'prefix\n```json\n{"a": 1}\n```\nsuffix'
    assert extract_json_from_text(raw) == {"a": 1}


def test_safe_parse_invalid_json_returns_raw():
    result = safe_parse_llm_json("not-json")
    assert result["parse_error"] is True
    assert "not-json" in result["raw_output"]
