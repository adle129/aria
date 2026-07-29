"""Unit tests for R1-CHG08 module source summaries (placeholder cache)."""

from app.services.module_source_summary_service import build_module_source_summaries


def test_build_placeholder_when_no_corpus_match():
    payload = build_module_source_summaries(
        rfq_modules={"functions_in_scope": ["Chassis", "BIW"]},
        comparison_table={
            "projects": [
                {
                    "engagement_id": "eng-a",
                    "project_name": "P1",
                    "summary": "无关摘要",
                }
            ]
        },
        similar_projects=[],
    )
    assert payload["mode"] == "placeholder"
    assert payload["in_scope"] == ["BIW", "Chassis"]
    chassis = payload["by_engagement"]["eng-a"]["Chassis"]
    assert chassis["status"] == "placeholder"
    assert chassis["bullets"]
    assert "BIW" in payload["by_engagement"]["eng-a"]
    assert "PM" not in payload["by_engagement"]["eng-a"]


def test_build_hint_from_similar_text():
    payload = build_module_source_summaries(
        rfq_modules={"functions_in_scope": ["Chassis"]},
        comparison_table={
            "projects": [{"engagement_id": "eng-b", "project_name": "P2"}]
        },
        similar_projects=[
            {
                "engagement_id": "eng-b",
                "content": "本项目底盘悬架开发包含转向与制动系统联调。",
            }
        ],
    )
    cell = payload["by_engagement"]["eng-b"]["Chassis"]
    assert cell["status"] == "hint"
    assert any("底盘" in b or "悬架" in b for b in cell["bullets"])


def test_empty_comparison_yields_empty_map():
    payload = build_module_source_summaries(
        rfq_modules={"functions_in_scope": ["PM"]},
        comparison_table={"projects": []},
    )
    assert payload["by_engagement"] == {}
