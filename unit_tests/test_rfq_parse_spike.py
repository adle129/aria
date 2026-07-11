"""Unit tests for RFQ parse spike validation (no Ollama)."""

from __future__ import annotations

import pytest

from app.services.rfq_parse_spike import (
    batch_chunks,
    is_milestone_chunk,
    is_overview_chapter,
    is_scope_chapter,
    merge_rfq_parse_parts,
    select_chunks_for_pass,
    truncate_rfq_text,
    validate_rfq_parse_result,
)
from app.services.rfq_rules_extractor import (
    extract_milestones_rules,
    extract_overview_rules,
    extract_rfq_rules,
    extract_scope_rules,
    infer_function_from_title,
    needs_overview_llm,
    needs_scope_llm,
)


def test_truncate_rfq_text_no_op():
    text, truncated = truncate_rfq_text("hello", 100)
    assert text == "hello"
    assert truncated is False


def test_truncate_rfq_text_truncates():
    text, truncated = truncate_rfq_text("abcdefghij", 5)
    assert text == "abcde"
    assert truncated is True


def test_chapter_selectors():
    assert is_overview_chapter("三、")
    assert is_overview_chapter("3.1")
    assert not is_overview_chapter("3.2")
    assert is_scope_chapter("四、")
    assert is_scope_chapter("4.1.2")
    assert not is_scope_chapter("3.1.1")


def test_milestone_excludes_scope_chunks():
    scope_chunk = {
        "chunk_chapter": "4.1.3.1.3",
        "content": "基于M0/EM1数据做整车DMU校核",
    }
    milestone_chunk = {
        "chunk_chapter": "3.2.2.3",
        "content": "3.2.3开发进度\n数据主要节点\nM0数据\n2022.02.25",
    }
    contract_chunk = {
        "chunk_chapter": "3.2.5.3",
        "content": "3.2.5.3 项目开展所用的软件由乙方提供",
    }
    assert not is_milestone_chunk(scope_chunk)
    assert is_milestone_chunk(milestone_chunk)
    assert not is_milestone_chunk(contract_chunk)


def test_select_chunks_body_fallback_for_short_rfq():
    chunks = [{"chunk_chapter": "body", "content": "Customer: ACME\nP1: 2026-01-01\nScope PM Chassis"}]
    overview = select_chunks_for_pass(chunks, "overview")
    assert len(overview) == 1
    assert overview[0]["chunk_chapter"] == "body"
    chunks = [
        {"chunk_chapter": "三、", "content": "overview"},
        {"chunk_chapter": "3.2", "content": "pm"},
        {"chunk_chapter": "4.1", "content": "scope"},
    ]
    overview = select_chunks_for_pass(chunks, "overview")
    scope = select_chunks_for_pass(chunks, "scope")
    assert [c["chunk_chapter"] for c in overview] == ["三、"]
    assert [c["chunk_chapter"] for c in scope] == ["4.1"]


def test_batch_chunks_splits_by_size():
    chunks = [
        {"chunk_chapter": "a", "content": "x" * 4000},
        {"chunk_chapter": "b", "content": "y" * 4000},
    ]
    batches = batch_chunks(chunks, max_chars=5000)
    assert len(batches) == 2


def test_merge_rfq_parse_parts():
    merged = merge_rfq_parse_parts(
        [
            {"project_name": "Proj", "functions_in_scope": ["PM"]},
            {"development_scope": [{"id": "4.1", "title": "GI", "function": "GI"}]},
            {"milestones": {"M1": "2022-04-30"}},
        ]
    )
    assert merged["project_name"] == "Proj"
    assert merged["functions_in_scope"] == ["PM"]
    assert len(merged["development_scope"]) == 1
    assert merged["milestones"]["M1"] == "2022-04-30"


def test_validate_ok_sample():
    payload = {
        "project_name": "Test",
        "customer": "ACME",
        "platform_type": "MEB",
        "functions_in_scope": ["PM", "Chassis"],
        "development_scope": [{"id": "4.2.1", "title": "底盘", "function": "Chassis"}],
        "milestones": {"P1": "2026-01-01"},
        "modules": [{"function": "Chassis", "module_name": "Front suspension"}],
        "timeline_months": 20,
    }
    report = validate_rfq_parse_result(payload)
    assert report["ok"] is True
    assert report["errors"] == []


def test_validate_parse_error():
    report = validate_rfq_parse_result({"parse_error": True, "raw_output": "not json"})
    assert report["ok"] is False
    assert "valid JSON" in report["errors"][0]


def test_validate_missing_functions():
    report = validate_rfq_parse_result(
        {
            "project_name": "X",
            "customer": "Y",
            "platform_type": "MEB",
            "functions_in_scope": [],
            "modules": [],
            "milestones": {},
        }
    )
    assert report["ok"] is False
    assert any("functions_in_scope" in e for e in report["errors"])


def test_validate_warns_missing_development_scope():
    report = validate_rfq_parse_result(
        {
            "project_name": "X",
            "customer": "Y",
            "platform_type": "MEB",
            "functions_in_scope": ["Chassis"],
            "modules": [{"function": "Chassis", "module_name": "Suspension"}],
            "milestones": {"P1": "2026-01-01"},
        }
    )
    assert report["ok"] is True
    assert any("development_scope" in w for w in report["warnings"])


_SAMPLE_MILESTONE_TABLE = """
3.2.3开发进度
序号 | 数据主要节点 | 车身/底盘/电器等
1 | M0数据 | 2022.02.25
2 | EM1数据 | 2022.03.25
3 | P1 | 2022-06-30
"""

_SAMPLE_OVERVIEW = """
3.1.1甲方委托乙方进行XXXX项目整车工程设计，包含整车总布置、车身系统、底盘系统、
电子电器系统、内外饰系统、结构与NVH、尺寸工程的设计开发工作。
该项目初步开发计划如下：2022年1月20日-2023年8月30日
"""


def test_extract_milestones_rules_from_table():
    table = """
3.2.3开发进度
序号 | 数据主要节点 | 车身/底盘/电器等
1 | M0数据 | 2022.02.25
2 | EM1数据 | 2022.03.25
3 | P1 | 2022-06-30
"""
    ms = extract_milestones_rules(table)
    assert ms.get("M0") == "2022-02-25"
    assert ms.get("EM1") == "2022-03-25"
    assert ms.get("P1") == "2022-06-30"


def test_extract_milestones_rules_word_cells():
    table = "3.2.3开发进度\x07数据主要节点\x07M0数据\x072022.02.25\x07EM1数据\x072022.03.25"
    ms = extract_milestones_rules(table)
    assert ms.get("M0") == "2022-02-25"
    assert ms.get("EM1") == "2022-03-25"


def test_extract_overview_rules_functions():
    overview = extract_overview_rules(_SAMPLE_OVERVIEW)
    assert overview["project_name"] == "XXXX项目"
    assert "Chassis" in overview["functions_in_scope"]
    assert "BIW" in overview["functions_in_scope"]
    assert "CAE" in overview["functions_in_scope"]


def test_infer_function_from_title():
    assert infer_function_from_title("4.1.3 底盘系统开发") == "Chassis"
    assert infer_function_from_title("4.1.6 CAE开发") == "CAE"


def test_extract_scope_rules_from_chunks():
    chunks = [
        {"chunk_chapter": "4.1.1 整车总布置开发", "content": ""},
        {"chunk_chapter": "4.1.1.1 P2阶段相应总布置工作", "content": ""},
        {"chunk_chapter": "4.1.2 车身系统开发", "content": ""},
        {"chunk_chapter": "3.1.1 foo", "content": ""},
    ]
    scope = extract_scope_rules(chunks)
    assert len(scope["development_scope"]) == 2
    assert any(d["id"] == "4.1.1" for d in scope["development_scope"])
    assert len(scope["modules"]) >= 2


def test_needs_overview_llm_when_unknown():
    assert needs_overview_llm({"project_name": "未知", "customer": "ACME", "platform_type": "MEB", "functions_in_scope": ["PM"]})
    assert not needs_overview_llm(
        {"project_name": "P", "customer": "C", "platform_type": "MEB", "functions_in_scope": ["PM"]}
    )


def test_needs_scope_llm_when_few_modules():
    assert needs_scope_llm({"modules": [{"function": "PM", "module_name": "x", "deliverables": []}]})
    assert not needs_scope_llm(
        {
            "modules": [{"function": "PM", "module_name": f"m{i}"} for i in range(10)],
            "development_scope": [{"id": "4.1.1", "title": "a"}, {"id": "4.1.2", "title": "b"}, {"id": "4.1.3", "title": "c"}],
        }
    )


def test_extract_rfq_rules_integration():
    text = _SAMPLE_OVERVIEW + _SAMPLE_MILESTONE_TABLE
    chunks = [
        {"chunk_chapter": "4.1.1 整车总布置开发", "content": "work"},
        {"chunk_chapter": "4.1.2 车身系统开发", "content": "work"},
    ]
    result = extract_rfq_rules(text, chunks)
    assert result["milestones"]["M0"] == "2022-02-25"
    assert len(result["modules"]) >= 2
    assert "Chassis" in result["functions_in_scope"] or "BIW" in result["functions_in_scope"]
