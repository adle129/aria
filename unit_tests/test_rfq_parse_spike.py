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
    summarize_module_functions,
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
            {
                "project_name": "Proj",
                "functions_in_scope": ["PM"],
                "modules": [
                    {
                        "function": "GI",
                        "module_name": "Package",
                        "l2_title": "工作内容",
                        "l3_title": "整车总布置开发",
                        "section_kind": "work_content",
                        "section_id": "4.1.1.1",
                    }
                ],
                "work_sections": [
                    {
                        "title": "工作内容",
                        "kind": "work_content",
                        "categories": [
                            {
                                "key": "整车总布置开发",
                                "label": "整车总布置开发",
                                "rows": [
                                    {
                                        "function": "GI",
                                        "module_name": "Package",
                                        "l2_title": "工作内容",
                                        "l3_title": "整车总布置开发",
                                    }
                                ],
                            }
                        ],
                    }
                ],
                "deliverable_groups": [
                    {"category": "整车总布置交付物", "function": "GI", "items": ["布置报告"]}
                ],
            },
            {"development_scope": [{"id": "4.1", "title": "GI", "function": "GI"}]},
            {"milestones": {"M1": "2022-04-30"}},
        ]
    )
    assert merged["project_name"] == "Proj"
    assert merged["functions_in_scope"] == ["PM"]
    assert len(merged["development_scope"]) == 1
    assert merged["milestones"]["M1"] == "2022-04-30"
    assert merged["deliverable_groups"][0]["category"] == "整车总布置交付物"
    assert merged["work_sections"][0]["title"] == "工作内容"


def test_summarize_module_functions_detects_name_collisions():
    diag = summarize_module_functions(
        [
            {"function": "未知", "module_name": "Package", "function_source": "unknown"},
            {"function": "GI", "module_name": "Package", "function_source": "llm"},
            {"function": "BIW", "module_name": "Body", "function_source": "keyword"},
        ]
    )
    assert diag["total"] == 3
    assert diag["known"] == 2
    assert diag["unknown"] == 1
    assert diag["name_collisions"] == [
        {"module_name": "Package", "functions": ["GI", "未知"]}
    ]


def test_merge_keeps_both_when_same_name_different_function():
    """Current merge key is (function, module_name) — collision stays until product fix."""
    merged = merge_rfq_parse_parts(
        [
            {
                "modules": [
                    {
                        "function": "未知",
                        "module_name": "Package",
                        "function_source": "unknown",
                        "l2_title": "工作内容",
                        "section_kind": "work_content",
                    }
                ]
            },
            {
                "modules": [
                    {
                        "function": "GI",
                        "module_name": "Package",
                        "function_source": "llm",
                        "l2_title": "工作内容",
                        "section_kind": "work_content",
                    }
                ]
            },
        ]
    )
    assert len(merged["modules"]) == 2
    assert {m["function"] for m in merged["modules"]} == {"未知", "GI"}


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


def test_work_sections_split_by_l2_path():
    base = "四、工作内容及要求"
    chunks = [
        {
            "chunk_chapter": "4.1.1 整车总布置开发",
            "content": "",
            "section_path": f"{base} > 4.1 工作内容 > 4.1.1 整车总布置开发",
        },
        {
            "chunk_chapter": "4.1.1.1 P2阶段相应总布置工作",
            "content": "",
            "section_path": f"{base} > 4.1 工作内容 > 4.1.1 整车总布置开发 > 4.1.1.1 P2阶段相应总布置工作",
        },
        {
            "chunk_chapter": "4.1.2 车身系统开发",
            "content": "",
            "section_path": f"{base} > 4.1 工作内容 > 4.1.2 车身系统开发",
        },
        {
            "chunk_chapter": "4.1.2.1 白车身结构设计",
            "content": "",
            "section_path": f"{base} > 4.1 工作内容 > 4.1.2 车身系统开发 > 4.1.2.1 白车身结构设计",
        },
        {
            "chunk_chapter": "4.3.1 乙方应保证所提交交付物的准确性、可靠性；",
            "content": "",
            "section_path": f"{base} > 4.3 技术要求 > 4.3.1 乙方应保证所提交交付物的准确性、可靠性；",
        },
        {
            "chunk_chapter": "4.4.1 交付物必须完整、无误，有效达到约定目标。",
            "content": "",
            "section_path": f"{base} > 4.4 交付物质量考核 > 4.4.1 交付物必须完整、无误，有效达到约定目标。",
        },
        {
            "chunk_chapter": "3.1.4 本项目开发范围的数据输入由甲方提供…",
            "content": "",
            "section_path": "三、项目要求 > 3.1 项目总体要求 > 3.1.4 本项目开发范围的数据输入由甲方提供…",
        },
    ]
    scope = extract_scope_rules(chunks)
    names = [str(m.get("module_name") or "") for m in scope["modules"]]
    assert any("P2阶段相应总布置工作" in n for n in names)
    assert any("白车身" in n for n in names)
    # Domain headings remain in canonical modules for F1.10; display folds them away when children exist.
    assert any(n == "整车总布置开发" for n in names)
    # 技术要求 / 质量条款不进 modules（维度匹配），进 work_sections
    assert not any("准确性" in n for n in names)
    assert not any("项目总体要求" in str(m.get("section_path") or "") for m in scope["modules"])

    by_title = {str(s["title"]): s for s in scope["work_sections"]}
    assert "工作内容" in by_title
    assert "技术要求" in by_title
    assert "交付物质量考核" in by_title  # path wording, not rewritten

    work_cats = {c["key"]: c for c in by_title["工作内容"]["categories"]}
    assert "整车总布置开发" in work_cats
    assert "车身系统开发" in work_cats
    assert any("白车身" in str(r.get("module_name")) for r in work_cats["车身系统开发"]["rows"])
    assert any("准确性" in str(r.get("module_name")) for r in by_title["技术要求"]["categories"][0]["rows"])
    assert any("完整" in str(r.get("module_name")) for r in by_title["交付物质量考核"]["categories"][0]["rows"])


def test_work_sections_use_path_wording_not_fixed_labels():
    base = "四、工作内容及要求"
    chunks = [
        {
            "chunk_chapter": "5.1.1 自定义域开发",
            "content": "",
            "section_path": f"{base} > 5.1 自定义二级目录 > 5.1.1 自定义域开发",
        },
        {
            "chunk_chapter": "5.1.1.1 叶子任务A",
            "content": "",
            "section_path": f"{base} > 5.1 自定义二级目录 > 5.1.1 自定义域开发 > 5.1.1.1 叶子任务A",
        },
        {
            "chunk_chapter": "5.2.1 自定义条款一",
            "content": "",
            "section_path": f"{base} > 5.2 另一类要求说明 > 5.2.1 自定义条款一",
        },
    ]
    scope = extract_scope_rules(chunks)
    titles = [str(s["title"]) for s in scope["work_sections"]]
    assert "自定义二级目录" in titles
    assert "另一类要求说明" in titles
    work = next(s for s in scope["work_sections"] if s["title"] == "自定义二级目录")
    assert any(c["label"] == "自定义域开发" for c in work["categories"])
    other = next(s for s in scope["work_sections"] if s["title"] == "另一类要求说明")
    assert any("自定义条款一" in str(r.get("module_name")) for c in other["categories"] for r in c["rows"])


def test_extract_scope_rules_from_chunks():
    base = "四、工作内容及要求"
    chunks = [
        {
            "chunk_chapter": "4.1.1 整车总布置开发",
            "content": "",
            "section_path": f"{base} > 4.1.1 整车总布置开发",
        },
        {
            "chunk_chapter": "4.1.1.1 P2阶段相应总布置工作",
            "content": "",
            "section_path": f"{base} > 4.1.1 整车总布置开发 > 4.1.1.1 P2阶段相应总布置工作",
        },
        {
            "chunk_chapter": "4.1.2 车身系统开发",
            "content": "",
            "section_path": f"{base} > 4.1.2 车身系统开发",
        },
        {
            "chunk_chapter": "3.1.1 foo",
            "content": "",
            "section_path": "三、项目要求 > 3.1.1 foo",
        },
    ]
    scope = extract_scope_rules(chunks)
    assert len(scope["development_scope"]) == 2
    assert any(d["id"] == "4.1.1" for d in scope["development_scope"])
    assert len(scope["modules"]) >= 2
    leaf = next(m for m in scope["modules"] if "P2" in str(m.get("module_name")))
    assert leaf["function"] == "GI"
    assert leaf["estimated_complexity"] == "未评估"


def test_extract_scope_keeps_canonical_leaves_folds_display_only():
    """modules stay one-row-per-heading; work_sections fold leaves into parents for UI."""
    base = "四、工作内容及要求"
    work = f"{base} > 4.1 工作内容"
    chunks = [
        {
            "chunk_chapter": "4.1.3 底盘系统开发",
            "content": "",
            "section_path": f"{work} > 4.1.3 底盘系统开发",
        },
        {
            "chunk_chapter": "4.1.3.1 P2阶段相应底盘/动力附件工作",
            "content": "",
            "section_path": f"{work} > 4.1.3 底盘系统开发 > 4.1.3.1 P2阶段相应底盘/动力附件工作",
        },
        {
            "chunk_chapter": "4.1.3.1.1 各个底盘系统竞品对比、选型报告",
            "content": "",
            "section_path": (
                f"{work} > 4.1.3 底盘系统开发 > 4.1.3.1 P2阶段相应底盘/动力附件工作"
                " > 4.1.3.1.1 各个底盘系统竞品对比、选型报告"
            ),
        },
        {
            "chunk_chapter": "4.1.3.1.2 完成底盘布置可行性分析",
            "content": "",
            "section_path": (
                f"{work} > 4.1.3 底盘系统开发 > 4.1.3.1 P2阶段相应底盘/动力附件工作"
                " > 4.1.3.1.2 完成底盘布置可行性分析"
            ),
        },
        {
            "chunk_chapter": "4.1.3.1.6 节点总结报告",
            "content": "",
            "section_path": (
                f"{work} > 4.1.3 底盘系统开发 > 4.1.3.1 P2阶段相应底盘/动力附件工作"
                " > 4.1.3.1.6 节点总结报告"
            ),
        },
        {
            "chunk_chapter": "4.1.3.2 P3阶段相应底盘/动力附件工作",
            "content": "",
            "section_path": f"{work} > 4.1.3 底盘系统开发 > 4.1.3.2 P3阶段相应底盘/动力附件工作",
        },
        {
            "chunk_chapter": "4.1.3.2.1 P3阶段校核报告",
            "content": "",
            "section_path": (
                f"{work} > 4.1.3 底盘系统开发 > 4.1.3.2 P3阶段相应底盘/动力附件工作"
                " > 4.1.3.2.1 P3阶段校核报告"
            ),
        },
        {
            "chunk_chapter": "4.1.1 整车总布置开发",
            "content": "",
            "section_path": f"{work} > 4.1.1 整车总布置开发",
        },
        {
            "chunk_chapter": "4.1.1.1 P2阶段相应总布置工作",
            "content": "",
            "section_path": f"{work} > 4.1.1 整车总布置开发 > 4.1.1.1 P2阶段相应总布置工作",
        },
    ]
    scope = extract_scope_rules(chunks)
    chassis_mods = [
        m
        for m in scope["modules"]
        if str(m.get("section_id") or "").startswith("4.1.3")
    ]
    mod_ids = [str(m.get("section_id")) for m in chassis_mods]
    assert "4.1.3.1.1" in mod_ids
    assert "4.1.3.1.6" in mod_ids
    assert "4.1.3.1" in mod_ids
    assert any("竞品对比" in str(m.get("module_name")) for m in chassis_mods)

    work = next(s for s in scope["work_sections"] if s["title"] == "工作内容")
    chassis_cat = next(c for c in work["categories"] if "底盘" in str(c.get("label") or ""))
    display_names = [str(r.get("module_name") or "") for r in chassis_cat["rows"]]
    assert display_names == [
        "P2阶段相应底盘/动力附件工作",
        "P3阶段相应底盘/动力附件工作",
    ]
    p2 = chassis_cat["rows"][0]
    assert "竞品对比" in str(p2.get("description") or "")
    assert "节点总结报告" in str(p2.get("description") or "")


def test_display_fold_synthesizes_parent_when_chunk_missing():
    """Canonical modules keep leaves; display view synthesizes parent from path."""
    base = "四、工作内容及要求"
    work = f"{base} > 4.1 工作内容"
    chunks = [
        {
            "chunk_chapter": "4.1.3 底盘系统开发",
            "content": "",
            "section_path": f"{work} > 4.1.3 底盘系统开发",
        },
        {
            "chunk_chapter": "4.1.3.1.1 各个底盘系统竞品对比、选型报告",
            "content": "",
            "section_path": (
                f"{work} > 4.1.3 底盘系统开发 > 4.1.3.1 P2阶段相应底盘/动力附件工作"
                " > 4.1.3.1.1 各个底盘系统竞品对比、选型报告"
            ),
        },
        {
            "chunk_chapter": "4.1.3.1.6 节点总结报告",
            "content": "",
            "section_path": (
                f"{work} > 4.1.3 底盘系统开发 > 4.1.3.1 P2阶段相应底盘/动力附件工作"
                " > 4.1.3.1.6 节点总结报告"
            ),
        },
        {
            "chunk_chapter": "4.1.3.2.1 P3阶段校核报告",
            "content": "",
            "section_path": (
                f"{work} > 4.1.3 底盘系统开发 > 4.1.3.2 P3阶段相应底盘/动力附件工作"
                " > 4.1.3.2.1 P3阶段校核报告"
            ),
        },
    ]
    scope = extract_scope_rules(chunks)
    mod_ids = [str(m.get("section_id")) for m in scope["modules"]]
    assert "4.1.3.1.1" in mod_ids
    assert "4.1.3.1.6" in mod_ids
    assert "4.1.3.1" not in mod_ids  # parent chunk absent → not in canonical modules

    work_sec = next(s for s in scope["work_sections"] if s["title"] == "工作内容")
    chassis = next(c for c in work_sec["categories"] if "底盘" in str(c.get("label") or ""))
    assert [r["section_id"] for r in chassis["rows"]] == ["4.1.3.1", "4.1.3.2"]
    assert "竞品对比" in str(chassis["rows"][0].get("description") or "")


def test_merge_keeps_canonical_modules_folds_work_sections_only():
    merged = merge_rfq_parse_parts(
        [
            {
                "project_name": "P",
                "customer": "C",
                "platform_type": "MEB",
                "functions_in_scope": ["Chassis"],
                "modules": [
                    {
                        "function": "Chassis",
                        "module_name": "P2阶段相应底盘/动力附件工作",
                        "section_id": "4.1.3.1",
                        "section_path": "四、工作内容及要求 > 4.1 工作内容 > 4.1.3 底盘系统开发 > 4.1.3.1 P2",
                        "l2_title": "工作内容",
                        "l3_title": "底盘系统开发",
                        "section_kind": "work_content",
                    },
                    {
                        "function": "Chassis",
                        "module_name": "节点总结报告",
                        "section_id": "4.1.3.1.6",
                        "section_path": (
                            "四、工作内容及要求 > 4.1 工作内容 > 4.1.3 底盘系统开发"
                            " > 4.1.3.1 P2 > 4.1.3.1.6 节点总结报告"
                        ),
                        "l2_title": "工作内容",
                        "l3_title": "底盘系统开发",
                        "section_kind": "work_content",
                    },
                ],
                "work_sections": [],
            },
        ]
    )
    mod_names = [str(m.get("module_name")) for m in merged["modules"]]
    assert "节点总结报告" in mod_names
    assert any("P2" in n for n in mod_names)

    work = next(s for s in merged["work_sections"] if s["title"] == "工作内容")
    rows = work["categories"][0]["rows"]
    assert len(rows) == 1
    assert "P2" in str(rows[0].get("module_name"))
    assert "节点总结报告" in str(rows[0].get("description") or "")


def test_display_rows_sorted_by_function_contiguous():
    from app.services.rfq_rules_extractor import _sort_rows_by_function

    rows = [
        {"function": "Interior", "module_name": "a", "section_id": "4.1.7.1"},
        {"function": "BIW", "module_name": "b", "section_id": "4.1.7.10"},
        {"function": "Interior", "module_name": "c", "section_id": "4.1.7.2"},
        {"function": "未知", "module_name": "z", "section_id": "4.1.7.99"},
    ]
    sorted_rows = _sort_rows_by_function(rows)
    assert [r["function"] for r in sorted_rows] == ["BIW", "Interior", "Interior", "未知"]


def test_extract_scope_inherits_parent_function_for_leaf():
    base = "四、工作内容及要求"
    chunks = [
        {
            "chunk_chapter": "4.1.1 整车总布置开发",
            "content": "",
            "section_path": f"{base} > 4.1.1 整车总布置开发",
        },
        {
            "chunk_chapter": "4.1.1.2.5 完成可行性分析并输出校核报告",
            "content": "",
            "section_path": f"{base} > 4.1.1 整车总布置开发 > 完成可行性分析并输出校核报告",
        },
    ]
    scope = extract_scope_rules(chunks)
    leaf = next(m for m in scope["modules"] if "可行性分析" in str(m.get("module_name")))
    assert leaf["function"] == "GI"
    assert leaf["function_source"] == "parent_section"
    assert leaf.get("function_inherited_from") == "4.1.1"
    assert leaf.get("section_id") == "4.1.1.2.5"


def test_needs_overview_llm_when_unknown():
    assert needs_overview_llm({"project_name": "未知", "customer": "ACME", "platform_type": "MEB", "functions_in_scope": ["PM"]})
    assert not needs_overview_llm(
        {"project_name": "P", "customer": "C", "platform_type": "MEB", "functions_in_scope": ["PM"]}
    )


def test_needs_scope_llm_when_few_modules():
    assert needs_scope_llm({"modules": [{"function": "PM", "module_name": "x", "deliverables": []}]})


def test_needs_scope_llm_when_deliverables_sparse():
    """Many modules without deliverables must still trigger scope LLM."""
    assert needs_scope_llm(
        {
            "modules": [
                {"function": "PM", "module_name": f"m{i}", "deliverables": []}
                for i in range(10)
            ],
            "development_scope": [
                {"id": "4.1.1", "title": "a"},
                {"id": "4.1.2", "title": "b"},
                {"id": "4.1.3", "title": "c"},
            ],
        }
    )


def test_needs_scope_llm_skips_when_deliverables_healthy():
    assert not needs_scope_llm(
        {
            "modules": [
                {"function": "PM", "module_name": f"m{i}", "deliverables": ["doc"]}
                for i in range(8)
            ],
        }
    )


def test_extract_rfq_rules_integration():
    text = _SAMPLE_OVERVIEW + _SAMPLE_MILESTONE_TABLE
    base = "四、工作内容及要求"
    chunks = [
        {
            "chunk_chapter": "4.1.1 整车总布置开发",
            "content": "work",
            "section_path": f"{base} > 4.1.1 整车总布置开发",
        },
        {
            "chunk_chapter": "4.1.2 车身系统开发",
            "content": "work",
            "section_path": f"{base} > 4.1.2 车身系统开发",
        },
    ]
    result = extract_rfq_rules(text, chunks)
    assert result["milestones"]["M0"] == "2022-02-25"
    assert len(result["modules"]) >= 2
    assert "Chassis" in result["functions_in_scope"] or "BIW" in result["functions_in_scope"]
