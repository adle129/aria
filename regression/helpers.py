"""Shared assertions for RFQ regression expectations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_expected(name: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "fixtures" / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def assert_parse_report_matches(report: dict[str, Any], expected: dict[str, Any]) -> None:
    assert report.get("parse_strategy") == expected.get("parse_strategy", "rules_first")
    validation = report.get("validation") or {}
    assert validation.get("ok") is True, validation

    result = report.get("result") or {}
    rules = expected.get("result") or {}

    for key in ("project_name", "customer", "platform_type"):
        if key in rules and rules[key] is not None:
            assert result.get(key), f"missing {key}"

    functions = result.get("functions_in_scope") or []
    assert isinstance(functions, list)
    for fn in rules.get("functions_in_scope_contains") or []:
        assert fn in functions, f"expected function {fn} in {functions}"

    modules = result.get("modules") or []
    mod_rules = rules.get("modules") or {}
    assert len(modules) >= int(mod_rules.get("min_count", 1))

    timeline = result.get("timeline_months")
    if "timeline_months" in mod_rules:
        bounds = mod_rules["timeline_months"]
        assert isinstance(timeline, (int, float))
        assert int(bounds["min"]) <= int(timeline) <= int(bounds["max"])

    dev_scope = result.get("development_scope") or []
    if "development_scope" in mod_rules:
        assert len(dev_scope) >= int(mod_rules["development_scope"].get("min_count", 0))
