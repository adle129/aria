"""Unit tests for §4.2 deliverable rules (SPK-F06)."""

from app.services.rfq_rules_extractor import (
    apply_deliverables_to_modules,
    enrich_unknown_module_functions,
    extract_deliverables_rules,
    infer_function_for_section,
    infer_function_from_title,
)


def test_infer_function_from_work_title():
    assert infer_function_from_title("P3阶段相应电子电器工作") == "EE"
    assert infer_function_from_title("内外饰系统开发") == "Interior"
    assert infer_function_from_title("4.2.6 CAE输入与输出") == "CAE"


def test_infer_function_for_section_hint():
    assert infer_function_for_section("4.2.6", "CAE输入") == "CAE"
    assert infer_function_for_section("4.2.4", "") == "EE"


def test_extract_deliverables_skips_section_intro():
    intro = (
        "4.2.6 CAE输入与输出内容详见表六，其中表中未能识别的支架类的分析也应视为协议内容。"
        "兼顾增程和纯电两种配置，分析阶段根据数据发布阶段定义。"
    )
    table = """
工作内容
1 | 碰撞分析 | 完成正面碰撞仿真报告
2 | NVH分析 | 完成模态分析数据
"""
    chunks = [
        {"chunk_chapter": "4.2.6 CAE开发", "content": intro},
        {"chunk_chapter": "4.2.6 CAE开发", "content": table},
    ]
    by_section, titles = extract_deliverables_rules(chunks)
    assert "4.2.6" in by_section
    assert len(by_section["4.2.6"]) == 2
    assert "详见表六" not in by_section["4.2.6"][0]
    assert titles.get("4.2.6") == "CAE开发"


def test_apply_deliverables_one_section_per_module():
    modules = [
        {"function": "CAE", "module_name": "CAE A", "deliverables": []},
        {"function": "CAE", "module_name": "CAE B", "deliverables": []},
        {"function": "EE", "module_name": "EE work", "deliverables": []},
    ]
    deliverables = {
        "4.2.6": ["碰撞分析报告", "NVH模态数据"],
        "4.2.4": ["线束布置数据"],
    }
    titles = {"4.2.6": "CAE", "4.2.4": "EE"}
    apply_deliverables_to_modules(modules, deliverables, titles)
    with_deliverables = [m for m in modules if m.get("deliverables")]
    assert len(with_deliverables) == 2
    assert modules[0]["deliverables"]
    assert not modules[1].get("deliverables")
    assert modules[2]["deliverables"]


def test_enrich_unknown_module_functions():
    modules = [{"function": "未知", "module_name": "P3阶段相应电子电器工作", "deliverables": []}]
    enrich_unknown_module_functions(modules)
    assert modules[0]["function"] == "EE"
