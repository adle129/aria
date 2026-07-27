from app.services.function_source_map_service import (
    FunctionSourceMapError,
    QUOTE_FUNCTION_KEYS,
    collect_candidate_engagement_ids,
    default_function_source_map,
    engagement_has_function_baseline,
    normalize_function_source_map,
    pick_preferred_engagement_id,
    resolve_in_scope_functions,
)
import pytest


def test_resolve_in_scope_functions_canonical_order():
    keys = resolve_in_scope_functions(
        {"functions_in_scope": ["Chassis", "pm", "UnknownModule"]}
    )
    assert keys == ["PM", "Chassis"]


def test_default_prefill_only_in_scope():
    m = default_function_source_map(
        in_scope=["PM", "BIW"],
        preferred_engagement_id="eng-a",
    )
    assert m["PM"] == "eng-a"
    assert m["BIW"] == "eng-a"
    assert m["Chassis"] is None
    assert set(m.keys()) == set(QUOTE_FUNCTION_KEYS)


def test_normalize_forces_out_of_scope_null_and_rejects_unknown():
    with pytest.raises(FunctionSourceMapError, match="未知模块"):
        normalize_function_source_map(
            {"NotASheet": "eng-a"},
            in_scope=["PM"],
            candidate_ids=["eng-a"],
        )

    out = normalize_function_source_map(
        {"PM": "eng-a", "Chassis": "eng-a"},
        in_scope=["PM"],
        candidate_ids=["eng-a"],
    )
    assert out["PM"] == "eng-a"
    assert out["Chassis"] is None


def test_normalize_rejects_engagement_outside_candidates():
    with pytest.raises(FunctionSourceMapError, match="不在当前"):
        normalize_function_source_map(
            {"PM": "eng-x"},
            in_scope=["PM"],
            candidate_ids=["eng-a"],
        )


def test_pick_and_collect_engagement_ids():
    projects = [{"project_name": "A", "engagement_id": "e1"}]
    similar = [{"metadata": {"engagement_id": "e2", "project_name": "B"}}]
    assert pick_preferred_engagement_id(projects, similar) == "e1"
    assert collect_candidate_engagement_ids(projects, similar) == ["e1", "e2"]


def test_engagement_has_function_baseline():
    assert engagement_has_function_baseline(
        {"functions": {"PM": {"total_man_days": 10, "positions": [{"position": "PM"}]}}},
        "PM",
    )
    assert not engagement_has_function_baseline(
        {"functions": {"PM": {"total_man_days": 0, "positions": []}}},
        "PM",
    )
