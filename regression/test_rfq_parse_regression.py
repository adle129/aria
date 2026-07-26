"""REG-P01/P02/P03: fixed RFQ samples → rules_first structural regression."""

from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document

from app.services.rfq_rules_first_service import run_parse_report
from helpers import assert_parse_report_matches, load_expected


def test_reg_p01_mock_chassis_rules_first(settings, mock_chassis_path):
    report = run_parse_report(settings, rfq_path=mock_chassis_path)
    assert_parse_report_matches(report, load_expected("mock_chassis_rfq.expected.json"))


def test_reg_p02_demo_multifunction_rules_first(settings, demo_multifunction_path):
    report = run_parse_report(settings, rfq_path=demo_multifunction_path)
    assert_parse_report_matches(report, load_expected("demo_multifunction_rfq.expected.json"))


def test_reg_p03_synthetic_timeline_rules_first(settings, tmp_path):
    """Minimal Chinese-shaped docx (rules-first overview + milestones) when no third customer RFQ exists."""
    doc = Document()
    # Must match extractor patterns: 整车工程 / 包含…设计开发工作 / 年月日—年月日 / M0+SOP dates.
    for line in (
        "进行Compact BEV整车工程开发技术协议",
        "甲方为Regression Synthetic汽车有限公司",
        "平台类型为BEV Compact SUV",
        "开发周期自2024年1月1日-2025年6月30日",
        "本项目包含项目管理、底盘的设计开发工作。",
        "工作内容及要求",
        "4.1 项目管理",
        "4.1.1 项目计划",
        "负责项目计划编制与进度跟踪。",
        "4.2 底盘",
        "4.2.1 前悬架",
        "前悬架结构设计与开发。",
        "开发进度",
        "M0 2024年1月1日",
        "SOP 2025年6月30日",
    ):
        doc.add_paragraph(line)
    path = tmp_path / "synthetic_timeline_rfq.docx"
    doc.save(path)

    report = run_parse_report(settings, rfq_path=path)
    assert_parse_report_matches(report, load_expected("synthetic_timeline_rfq.expected.json"))
