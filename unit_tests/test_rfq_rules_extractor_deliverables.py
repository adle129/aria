"""Unit tests for deliverable table rules + work-item alignment (number-free)."""

from app.services.rfq_rules_extractor import (
    _normalize_deliverable_category,
    align_deliverables_to_work_items,
    apply_deliverables_to_modules,
    enrich_unknown_module_functions,
    extract_deliverables_rules,
    infer_function_for_section,
    infer_function_from_title,
)


def test_normalize_deliverable_category():
    assert (
        _normalize_deliverable_category(
            "表一：整车总布置交付物清单表【R = Responsibility（负责）】"
        )
        == "整车总布置交付物"
    )
    assert _normalize_deliverable_category("表二：车身系统交付物清单表") == "车身系统交付物"


def test_infer_function_from_work_title():
    assert infer_function_from_title("P3阶段相应电子电器工作") == "EE"
    assert infer_function_from_title("内外饰系统开发") == "Interior"
    assert infer_function_from_title("CAE输入与输出") == "CAE"


def test_infer_function_for_section_from_title_only():
    assert infer_function_for_section("any-id", "CAE输入") == "CAE"
    assert infer_function_for_section("any-id", "尺寸工程输入与输出") == "GI"
    assert infer_function_for_section("any-id", "") == "未知"
    assert infer_function_for_section("any-id", "底盘系统输入与输出") == "Chassis"


def test_extract_deliverables_skips_section_intro():
    intro = (
        "CAE输入与输出内容详见表六，其中表中未能识别的支架类的分析也应视为协议内容。"
        "兼顾增程和纯电两种配置，分析阶段根据数据发布阶段定义。"
    )
    table = """
工作内容
1 | 碰撞分析 | 完成正面碰撞仿真报告
2 | NVH分析 | 完成模态分析数据
"""
    chunks = [
        {"chunk_chapter": "CAE开发", "content": intro},
        {"chunk_chapter": "CAE开发", "content": table},
    ]
    by_function, labels, groups = extract_deliverables_rules(chunks)
    assert "CAE" in by_function
    assert len(by_function["CAE"]) == 2
    assert "详见表六" not in by_function["CAE"][0]


def test_apply_deliverables_domain_only():
    modules = [
        {
            "function": "CAE",
            "module_name": "CAE A",
            "deliverables": [],
            "section_id": "1.2.3",
        },
        {
            "function": "CAE",
            "module_name": "CAE leaf",
            "deliverables": [],
            "section_id": "1.2.3.1.1",
        },
        {
            "function": "EE",
            "module_name": "EE work",
            "deliverables": [],
            "section_id": "1.2.4",
        },
    ]
    deliverables = {
        "CAE": ["碰撞分析报告", "NVH模态数据"],
        "EE": ["线束布置数据"],
    }
    apply_deliverables_to_modules(modules, deliverables)
    assert modules[0]["deliverables"] == ["碰撞分析报告", "NVH模态数据"]
    assert not modules[1].get("deliverables")
    assert modules[2]["deliverables"] == ["线束布置数据"]


def test_align_deliverables_to_work_items_precise():
    modules = [
        {
            "function": "GI",
            "module_name": "完成总体布置分析报告并提交",
            "deliverables": [],
            "section_id": "1.1.1.1.5",
        },
        {
            "function": "BIW",
            "module_name": "编写专利排查报告",
            "deliverables": [],
            "section_id": "1.1.2.1.3",
        },
        {
            "function": "BIW",
            "module_name": "P2阶段相应车身工作",
            "deliverables": [],
            "section_id": "1.1.2.1",
        },
    ]
    deliverables = {
        "GI": ["总体布置分析报告", "舱室布置分析报告"],
        "BIW": ["标准件清单", "专利排查报告", "M1数模"],
    }
    align_deliverables_to_work_items(modules, deliverables)
    assert modules[0]["deliverables"] == ["总体布置分析报告"]
    assert modules[0]["deliverables_source"] == "aligned"
    assert modules[1]["deliverables"] == ["专利排查报告"]
    assert not modules[2].get("deliverables")


def test_align_by_function_ignores_table_order():
    """Domain comes from title keywords — table order in the RFQ does not matter."""
    modules = [
        {
            "function": "Chassis",
            "module_name": "完成悬架布置及运动校核报告",
            "deliverables": [],
            "section_id": "9.9.9.1.2",
        }
    ]
    deliverables = {
        "Chassis": ["悬架布置及运动校核报告", "轮胎包络数据"],
        "GI": ["总体布置分析报告"],
    }
    align_deliverables_to_work_items(modules, deliverables)
    assert modules[0]["deliverables"] == ["悬架布置及运动校核报告"]


def test_align_does_not_cross_domain():
    modules = [
        {
            "function": "BIW",
            "module_name": "完成总体布置分析报告",
            "deliverables": [],
            "section_id": "1.1.2.1.1",
        }
    ]
    deliverables = {
        "GI": ["总体布置分析报告"],
        "BIW": ["标准件清单"],
    }
    align_deliverables_to_work_items(modules, deliverables)
    assert not modules[0].get("deliverables")


def test_extract_deliverables_word_cell_stream():
    body = """
表一：总布置交付物清单（R = Responsibility）
序号
 | 条件
 | 交付物清单
 | 交付物格式
 | 节点
 | 乙方
 | 甲方
 | 
 | 1
 | 常规输入
 | 总体布置方案报告
 | PPT
 | P2
 | R
 | A
 | 
 | 2
 | 
 | 前舱布置可行性报告
 | PPT
 | P2
 | R
 | A
"""
    chunks = [{"chunk_chapter": "整车总布置", "content": body}]
    by_function, _, _groups = extract_deliverables_rules(chunks)
    assert "GI" in by_function
    assert any(x.startswith("总体布置方案报告") for x in by_function["GI"])
    assert any(x.startswith("前舱布置可行性报告") for x in by_function["GI"])


def test_extract_deliverables_ee_without_serial():
    body = """
表四：电器系统交付物清单表
序号
 | 条件
 | 交付物清单
 | 交付物格式
 | 节点
 | 乙方
 | 甲方
 | 
 | 1.竞品车
 | 2.整车质量目标
 | 专利排查报告
 | PPT
 | P2
 | R
 | A
 | S
 | 
 | 标准件清单
 | EXCELL
 | P2
 | R
 | A
 | S
 | 
 | 初版ICD（物理&电器）
 | PPT /EXCEL
 | P2
 | R
 | A
"""
    chunks = [{"chunk_chapter": "电器系统", "content": body}]
    by_function, _, _groups = extract_deliverables_rules(chunks)
    assert any(x.startswith("专利排查报告") for x in by_function["EE"])
    assert any(x.startswith("标准件清单") for x in by_function["EE"])
    assert any(x.startswith("初版ICD（物理&电器）") for x in by_function["EE"])


def test_extract_deliverables_accepts_parenthesized_excel_format():
    body = """
表一：整车总布置交付物清单表
序号
 | 条件
 | 交付物清单
 | 交付物格式
 | 节点
 | 乙方
 | 甲方
 | 
 | 1
 | 
 | 总体布置分析报告
 | PPT
 | P2
 | R
 | A
 | 
 | 2
 | 
 | 造型可行性分析报告（造型各阶段ECR）
 | (Excel)
 | P2-P3
 | R
 | A
 | 
 | 3
 | 
 | 人机校核报告（初版）
 | PPT
 | P2
 | R
 | A
"""
    text = "整车总布置输入与输出内容见表一。\n" + body
    _by, _lab, groups = extract_deliverables_rules([], text=text)
    gi = next(g for g in groups if "总布置" in g["category"])
    assert len(gi["items"]) == 3
    assert any("造型可行性分析报告（造型各阶段ECR）" in x for x in gi["items"])
    assert any(x.endswith("（P2）") or "（P2）" in x for x in gi["items"])
    assert any("P2-P3" in x for x in gi["items"])


def test_extract_deliverables_cae_numbered_work_content():
    body = """
表六：CAE交付物清单表
类别
 | 编号
 | 工作内容
 | M0
 | M1
 | M2
 | 试验验证
 | 备注
 | 交付物
 | 
 | 刚度分析
 | 白车身
 | 1
 | 白车身关键安装点刚度分析
 | ●
 | ●
 | ●
 | 
 | 
 | 模型、结果、报告
 | 
 | 
 | 2
 | 风窗盖板刚度分析
 | ●
 | ●
 | ●
 | 
 | 
 | 模型、结果、报告
 | 
 | 开启件
 | 3
 | 前舱盖扭转刚度分析
 | ●
 | ●
 | ●
 | 
 | 
 | 模型、结果、报告
"""
    text = "CAE输入与输出内容见表六。\n" + body
    by_function, _lab, groups = extract_deliverables_rules([], text=text)
    assert "CAE" in by_function
    assert by_function["CAE"][:3] == [
        "白车身关键安装点刚度分析",
        "风窗盖板刚度分析",
        "前舱盖扭转刚度分析",
    ]
    cae_groups = [g for g in groups if "CAE" in g["category"]]
    assert cae_groups
    assert len(cae_groups[0]["items"]) == 3


def test_extract_deliverables_尺寸工程_交付清单_header():
    body = """
表七：尺寸工程交付物清单表
序号
 | 输入条件
 | 交付清单
 | 交付物格式
 | 节点
 | 乙方
 | 甲方
 | 
 | 1
 | 1.整车CAS面主断面
 | 2.整车外观造型
 | 3、整车内饰造型
 | 4．基础公差
 | 初版整车内外观DTS
 | PPT
 | P2
 | R
 | A
 | -
 | 
 | 2
 | 
 | 工程变更申请单ECR（内外CAS面、主断面尺寸SE分析）
 | EXCEL
 | P2
 | R
 | A
 | -
 | 
 | 3
 | 
 | 阶段总结报告
 | PPT
 | P2
 | R
 | A
 | -
 | 
 | 4
 | 
 | 阶段总结报告
 | PPT
 | P3
 | R
 | A
"""
    text = "尺寸工程输入与输出内容见表七。工作方向必须包含但不局限于表中所列项目。\n" + body
    by_function, labels, groups = extract_deliverables_rules([], text=text)
    assert "GI" in by_function
    assert "初版整车内外观DTS（P2）" in by_function["GI"] or any(
        x.startswith("初版整车内外观DTS") for x in by_function["GI"]
    )
    assert any(
        x.startswith("工程变更申请单ECR（内外CAS面、主断面尺寸SE分析）")
        for x in by_function["GI"]
    )
    size_groups = [g for g in groups if "尺寸工程" in g["category"]]
    assert size_groups
    items = size_groups[0]["items"]
    assert len(items) == 4
    assert "阶段总结报告（P2）" in items
    assert "阶段总结报告（P3）" in items
    assert any(x.startswith("初版整车内外观DTS") for x in items)


def test_fill_deliverables_from_work_items():
    from app.services.rfq_rules_extractor import fill_deliverables_from_work_items

    modules = [
        {
            "function": "BIW",
            "module_name": "完成下部车身布置可行性分析报告",
            "deliverables": [],
        },
        {"function": "BIW", "module_name": "车身系统开发", "deliverables": []},
    ]
    fill_deliverables_from_work_items(modules)
    assert modules[0]["deliverables"] == ["完成下部车身布置可行性分析报告"]
    assert modules[0]["deliverables_source"] == "work_item"
    assert not modules[1].get("deliverables")


def test_enrich_unknown_module_functions():
    modules = [{"function": "未知", "module_name": "P3阶段相应电子电器工作", "deliverables": []}]
    enrich_unknown_module_functions(modules)
    assert modules[0]["function"] == "EE"


def test_extract_deliverables_清单_header_columns():
    table = """
序号 | 条件 | 交付物清单 | 交付物格式 | 节点
1 | 常规 | 完成整车总布置方案 | CATIA | P2
2 | 常规 | 完成尺寸工程校核报告 | PDF | P3
"""
    chunks = [{"chunk_chapter": "总布置与尺寸工程", "content": table}]
    by_function, _, _groups = extract_deliverables_rules(chunks)
    assert by_function["GI"] == ["完成整车总布置方案（P2）", "完成尺寸工程校核报告（P3）"]


def test_extract_deliverables_covers_multiple_domains_by_caption():
    titles = {
        "总布置": "GI",
        "车身": "BIW",
        "底盘": "Chassis",
        "电子电器": "EE",
        "内外饰": "Interior",
        "CAE": "CAE",
        "试验验证": "Test validation",
    }
    chunks = []
    for title, _fn in titles.items():
        chunks.append(
            {
                "chunk_chapter": f"{title}系统",
                "content": (
                    f"表：{title}交付物清单\n"
                    f"序号 | 条件 | 交付物清单 | 交付物格式 | 节点\n"
                    f"1 | 常规 | {title}交付物A报告 | PDF | P2\n"
                    f"2 | 常规 | {title}交付物B数据 | CATIA | P3\n"
                ),
            }
        )
    by_function, _, _groups = extract_deliverables_rules(chunks)
    for title, fn in titles.items():
        assert fn in by_function, title
        assert len(by_function[fn]) == 2


def test_extract_deliverables_skips_intro_only_chunk():
    intro = (
        "车身开发内容详见表二，其中表中未能识别的支架类的分析也应视为协议内容。"
        "兼顾增程和纯电两种配置，分析阶段根据数据发布阶段定义。"
    )
    chunks = [{"chunk_chapter": "车身开发", "content": intro}]
    by_function, _, _groups = extract_deliverables_rules(chunks)
    assert "BIW" not in by_function
