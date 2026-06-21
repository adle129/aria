import json
import re
from typing import Any


def extract_json_from_text(text: str) -> dict[str, Any]:
    """Parse JSON from LLM output, including ```json fenced blocks."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    return json.loads(cleaned)


def safe_parse_llm_json(text: str) -> dict[str, Any]:
    try:
        return extract_json_from_text(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"raw_output": text, "parse_error": True}
