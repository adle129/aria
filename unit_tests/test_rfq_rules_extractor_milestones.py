"""Unit tests for milestone rules (SPK-F05)."""

from app.services.rfq_rules_extractor import extract_milestones_rules


def test_milestones_row_oriented_p1_p4_sop():
    text = """
3.2.3开发进度
序号 | 数据主要节点 | 日期
1 | M0数据 | 2022.02.25
2 | EM1数据 | 2022.03.25
3 | P1 | 2022年6月30日
4 | P4节点 | 2023.03.15
5 | SOP | 2023.08.30
"""
    ms = extract_milestones_rules(text)
    assert ms["M0"] == "2022-02-25"
    assert ms["EM1"] == "2022-03-25"
    assert ms["P1"] == "2022-06-30"
    assert ms["P4"] == "2023-03-15"
    assert ms["SOP"] == "2023-08-30"


def test_milestones_acceptance_table_p2_node():
    text = """
验收阶段
阶段 | 节点名称 | 计划完成
1 | P2节点 | 2022年6月30日
2 | P3节点 | 2022年12月15日
3 | P5节点 | 2023年5月20日
"""
    ms = extract_milestones_rules(text)
    assert ms["P2"] == "2022-06-30"
    assert ms["P3"] == "2022-12-15"
    assert ms["P5"] == "2023-05-20"


def test_milestones_alias_sop_from_production():
    text = """
开发进度
项目启动 Kick-off 于 2022.01.20
量产投产目标 2023年8月30日
"""
    ms = extract_milestones_rules(text)
    assert ms.get("P1") == "2022-01-20" or "P1" in ms
    assert ms["SOP"] == "2023-08-30"


def test_milestones_merge_chunks_without_wiping():
    text = """
3.2.3开发进度
1 | M0数据 | 2022.02.25
2 | EM1数据 | 2022.03.25
"""
    chunks = [
        {
            "chunk_chapter": "验收表",
            "content": "验收阶段\n1 | P1节点 | 2022.06.30\n2 | P4节点 | 2023.03.15\n3 | SOP | 2023.08.30",
        }
    ]
    ms = extract_milestones_rules(text, chunks)
    assert ms["M0"] == "2022-02-25"
    assert ms["EM1"] == "2022-03-25"
    assert ms["P1"] == "2022-06-30"
    assert ms["P4"] == "2023-03-15"
    assert ms["SOP"] == "2023-08-30"


def test_milestones_wide_separator_x07():
    text = (
        "开发进度\n"
        "M0数据\x072022.02.25\n"
        "P1\x072022年6月30日\n"
        "P4\x072023.03.15\n"
    )
    ms = extract_milestones_rules(text)
    assert ms["M0"] == "2022-02-25"
    assert ms["P1"] == "2022-06-30"
    assert ms["P4"] == "2023-03-15"
