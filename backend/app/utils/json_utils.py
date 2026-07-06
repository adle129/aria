import json
import re
from typing import Any


def extract_json_from_text(text: str) -> Any:
    """Parse JSON from LLM output, including ```json fenced blocks."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    return json.loads(cleaned)


def normalize_llm_json(data: Any) -> dict[str, Any]:
    """Coerce LLM JSON (sometimes a bare list) into prompt-spec object shape."""
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        if not data:
            return {"parse_error": True, "raw_shape": "empty_list"}
        if not all(isinstance(item, dict) for item in data):
            return {"parse_error": True, "raw_shape": "list_non_objects"}

        modules = [item for item in data if "module_name" in item]
        scope = [item for item in data if "title" in item and "id" in item]
        merged: dict[str, Any] = {}
        if modules:
            merged["modules"] = modules
        if scope:
            merged["development_scope"] = scope
        if merged:
            return merged

        first = data[0]
        if "module_name" in first or ("function" in first and "description" in first):
            return {"modules": data}
        if "title" in first or "id" in first:
            return {"development_scope": data}
        if "in_scope" in first or "dimension_id" in first:
            return {"items": data}
        return {"items": data}

    return {"parse_error": True, "raw_shape": type(data).__name__}


def safe_parse_llm_json(text: str) -> dict[str, Any]:
    try:
        parsed = extract_json_from_text(text)
        return normalize_llm_json(parsed)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"raw_output": text, "parse_error": True}
