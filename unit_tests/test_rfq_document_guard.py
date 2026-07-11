"""Unit tests for RFQ / 技术协议 document content guard."""

import pytest

from app.services.rfq_document_guard import (
    RFQ_INSUFFICIENT_STRUCTURE_MSG,
    RFQ_NOT_EXPECTED_MSG,
    RfqDocumentRejectedError,
    assert_looks_like_rfq,
    assert_rfq_parse_quality,
    looks_like_rfq,
    normalize_rfq_text,
)

_PAD = "说明" * 120  # keep synthetic bodies above min length

_R1_GOAL_SNIPPET = (
    "R1 总目标（签字时必须具备）\n"
    "M0 通过（GPU、数据盘、Ollama、Docker、内网可访问）\n"
    "全类型 Engagement 入库（RFQ + Q_A + 报价 Excel + 历史方案）\n"
    "3 份 RFQ 对标 全流程（上传 → 解析 → 维度确认 → 对比矩阵）\n"
    + _PAD
)


def test_normalize_collapses_cjk_spaces():
    assert "技术协议书" in normalize_rfq_text("技 术 协 议 书")


def test_reject_empty_and_short():
    assert looks_like_rfq("") is False
    assert looks_like_rfq("短") is False
    with pytest.raises(RfqDocumentRejectedError, match="不像 RFQ"):
        assert_looks_like_rfq("会议纪要")


def test_reject_meeting_minutes():
    text = (
        "周例会纪要\n"
        "出席：张三、李四\n"
        "议题：进度同步与下周安排\n"
        "决议：继续推进原型验证，下周再议预算。\n"
        + _PAD
    )
    assert looks_like_rfq(text) is False
    with pytest.raises(RfqDocumentRejectedError) as exc:
        assert_looks_like_rfq(text)
    assert str(exc.value) == RFQ_NOT_EXPECTED_MSG


def test_reject_r1_goal_with_rfq_mentions_in_body():
    assert looks_like_rfq(_R1_GOAL_SNIPPET) is False
    with pytest.raises(RfqDocumentRejectedError) as exc:
        assert_looks_like_rfq(_R1_GOAL_SNIPPET)
    assert str(exc.value) == RFQ_NOT_EXPECTED_MSG


def test_pass_spaced_technical_agreement_title():
    text = "XX新能源汽车有限公司\nXXXX项目整车工程设计\n 技 术 协 议 书\n\n编制：\n" + _PAD
    assert looks_like_rfq(text) is True
    assert_looks_like_rfq(text)


def test_pass_deliverable_and_section_42():
    text = "四、工作内容及要求\n4.2.1 车身\n交付物清单\n序号|交付物|节点\n" + _PAD
    assert looks_like_rfq(text) is True


def test_pass_title_rfq_only_in_document_head():
    text = "RFQ — Mock Chassis Development Project\nCustomer: Mock Auto GmbH\n" + _PAD
    assert looks_like_rfq(text) is True


def test_body_rfq_mention_without_title_or_structure_fails():
    text = "项目计划与里程碑说明\n" + _PAD + "\n其中包含 3 份 RFQ 对标流程说明。"
    assert looks_like_rfq(text) is False


def test_pass_via_rules_stats_without_keywords():
    text = "纯叙述性长文，无结构关键词。" + _PAD
    assert looks_like_rfq(text) is False
    assert looks_like_rfq(text, {"milestones_count": 2, "modules_count": 0, "development_scope_count": 0}) is True
    assert_looks_like_rfq(text, {"milestones_count": 0, "modules_count": 1, "development_scope_count": 0})


def test_parse_quality_rejects_empty_rules():
    with pytest.raises(RfqDocumentRejectedError) as exc:
        assert_rfq_parse_quality(
            {"milestones_count": 0, "modules_count": 0, "development_scope_count": 0},
        )
    assert str(exc.value) == RFQ_INSUFFICIENT_STRUCTURE_MSG


def test_parse_quality_passes_when_rules_hit():
    assert_rfq_parse_quality({"milestones_count": 1, "modules_count": 0, "development_scope_count": 0}) is None


def test_structure_only_passes_type_but_fails_quality():
    text = "四、工作内容及要求\n4.2.1 车身\n交付物清单\n" + _PAD
    assert_looks_like_rfq(text)
    with pytest.raises(RfqDocumentRejectedError) as exc:
        assert_rfq_parse_quality(
            {"milestones_count": 0, "modules_count": 0, "development_scope_count": 0},
        )
    assert str(exc.value) == RFQ_INSUFFICIENT_STRUCTURE_MSG
