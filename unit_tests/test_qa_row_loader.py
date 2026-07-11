"""Unit tests for Q_A row loader."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from app.services.ingest.qa_row_loader import format_qa_row_content, load_qa_rows


def test_format_qa_row_content_labels_and_order():
    payload = {
        "no": "1",
        "area": "Packaging",
        "author": "ZYH",
        "question": "Who will do the benchmark? 谁做对标？",
        "assumption": "EDAG assumption text",
        "answer_by_customer": "Customer, will provide to 我司",
        "impact": "高",
        "history_reference": "project-A / Q_A.xlsx",
    }
    text = format_qa_row_content(payload)
    assert text.startswith("Area: Packaging")
    assert "Question: Who will do the benchmark?" in text
    assert "No: 1" in text
    assert "Author: ZYH" in text
    assert "Assumption 我司: EDAG assumption text" in text
    assert "Answer by customer: Customer, will provide to 我司" in text
    assert "Impact: 高" in text
    assert text.index("Area:") < text.index("Question:")
    assert text.index("Question:") < text.index("No:")


def test_format_qa_row_content_keeps_empty_core_columns():
    payload = {
        "no": "2",
        "area": "Chassis",
        "author": "",
        "question": "Spring rate definition?",
        "assumption": "",
        "answer_by_customer": "",
    }
    text = format_qa_row_content(payload)
    assert "Area: Chassis" in text
    assert "Assumption 我司:" in text
    assert "Answer by customer:" in text
    assert "Customer" not in text


def test_load_qa_rows_from_workbook(tmp_path: Path):
    path = tmp_path / "Q_A_test.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["", "", "", "", "", "", "", ""])
    ws.append(["No.", "Area", "Author", "Question", "Assumption", "Answer", "Impact", "History"])
    ws.append(["1", "Packaging", "ZYH", "Bilingual Q?", "Our assume", "Cust ans", "", ""])
    wb.save(path)

    rows = load_qa_rows(path)
    assert len(rows) == 1
    row = rows[0]
    assert row["chunk_chapter"] == "Packaging"
    assert row["content"].startswith("Area: Packaging")
    assert "Question: Bilingual Q?" in row["content"]
    assert "Assumption 我司: Our assume" in row["content"]
    assert "Answer by customer: Cust ans" in row["content"]
    assert row["metadata"]["area"] == "Packaging"


def test_load_qa_rows_skips_blank_question(tmp_path: Path):
    path = tmp_path / "empty_q.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append([None] * 8)
    ws.append(["No.", "Area", "Author", "Question", "Assumption", "Answer", "Impact", "History"])
    ws.append(["1", "ALL", "X", None, None, None, None, None])
    wb.save(path)
    assert load_qa_rows(path) == []
