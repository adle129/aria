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
    """Minimal docx when no third customer RFQ is available."""
    doc = Document()
    doc.add_paragraph("Customer: Regression Synthetic OEM")
    doc.add_paragraph("RFQ — Compact BEV Platform Development")
    doc.add_paragraph("Platform: MEB")
    doc.add_paragraph("Project Duration: 18 months")
    doc.add_paragraph("Scope includes Chassis design and PM coordination.")
    doc.add_paragraph("Front suspension and rear suspension structural development.")
    path = tmp_path / "synthetic_timeline_rfq.docx"
    doc.save(path)

    report = run_parse_report(settings, rfq_path=path)
    assert_parse_report_matches(report, load_expected("synthetic_timeline_rfq.expected.json"))
