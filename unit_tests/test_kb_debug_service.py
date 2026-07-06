"""Unit tests for KB debug service (DEV RAG validation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.services.kb_debug_service import KBDebugService
from app.services.knowledge_index_service import flatten_preview_chunks


@pytest.fixture
def debug_settings(tmp_path):
    return Settings(
        aria_ui_profile="dev",
        kb_debug_enabled=True,
        mock_rag=False,
        chroma_path=str(tmp_path / "chroma"),
        feedback_path=str(tmp_path / "feedback.jsonl"),
        validation_corpus_path=str(tmp_path / "corpus"),
    )


def test_flatten_preview_chunks_from_synthetic_report():
    report = {
        "corpus_path": "/tmp/x",
        "rfq": {
            "path": "RFQ.docx",
            "chunks": [
                {
                    "chunk_id": "c1",
                    "chunk_type": "chapter",
                    "chunk_chapter": "3.1",
                    "content": "scope text",
                    "metadata": {"doc_type": "rfq", "source_doc": "RFQ.docx"},
                }
            ],
        },
        "qa": {"path": "Q_A.xlsx"},
    }
    chunks = flatten_preview_chunks(report)
    assert len(chunks) >= 1
    assert chunks[0]["chunk_id"] == "c1"


def test_submit_feedback_writes_jsonl(debug_settings, tmp_path):
    svc = KBDebugService(debug_settings)
    record = svc.submit_feedback(
        {
            "feedback_type": "chunk_ok",
            "chunk_id": "abc",
            "source_context": "chunk_inspector",
        }
    )
    assert record["id"]
    assert Path(debug_settings.feedback_path).exists()


def test_index_corpus_rejects_mock_rag(debug_settings, tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "readme.txt").write_text("x", encoding="utf-8")
    svc = KBDebugService(Settings(**{**debug_settings.model_dump(), "mock_rag": True}))
    with pytest.raises(Exception, match="MOCK_RAG"):
        svc.index_corpus(corpus)


def test_preview_file_persists_cache(debug_settings, tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    qa_src = Path(__file__).resolve().parents[1] / "backend" / "data" / "templates" / "qa_template.xlsx"
    if not qa_src.exists():
        pytest.skip("qa_template missing")
    import shutil

    shutil.copy(qa_src, corpus / "Q_A_模板.xlsx")

    svc1 = KBDebugService(debug_settings)
    report = svc1.preview_file("Q_A_模板.xlsx", corpus)
    assert report["qa"]["row_chunks"] >= 1

    svc2 = KBDebugService(debug_settings)
    chunks = svc2.list_chunks()
    assert chunks["total"] >= 1
    assert chunks["target_file"] == "Q_A_模板.xlsx"


def test_list_corpus_files(debug_settings, tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "Q_A_模板.xlsx").write_bytes(b"x")
    svc = KBDebugService(debug_settings)
    files = svc.list_corpus_files(corpus)
    assert len(files) == 1
    assert files[0]["file_role"] == "qa"


def test_list_chunks_empty_without_preview(debug_settings):
    svc = KBDebugService(debug_settings)
    out = svc.list_chunks()
    assert out["total"] == 0


def test_list_chunks_respects_limit_and_offset(debug_settings, monkeypatch):
    chunks = [
        {
            "chunk_id": f"c{i}",
            "chunk_type": "chapter",
            "chunk_chapter": f"sec-{i}",
            "content": f"body-{i}",
            "metadata": {"doc_type": "rfq", "source_doc": "RFQ.doc"},
        }
        for i in range(144)
    ]
    report = {
        "corpus_path": str(debug_settings.validation_corpus_path),
        "target_file": "RFQ.doc",
        "rfq": {"path": "RFQ.doc", "chunks": chunks},
    }
    monkeypatch.setattr("app.services.kb_debug_service.load_preview", lambda _settings: report)

    svc = KBDebugService(debug_settings)
    page = svc.list_chunks(limit=100, offset=0)
    assert page["total"] == 144
    assert len(page["items"]) == 100
    assert page["items"][-1]["chunk_chapter"] == "sec-99"

    full = svc.list_chunks(limit=2000, offset=0)
    assert len(full["items"]) == 144
    assert full["items"][-1]["chunk_chapter"] == "sec-143"


def test_qa_areas_from_cache_and_list_chunks(debug_settings, monkeypatch):
    report = {
        "corpus_path": str(debug_settings.validation_corpus_path),
        "target_file": "Q_A_模板.xlsx",
        "file_role": "qa",
        "qa": {
            "path": "Q_A_模板.xlsx",
            "areas": ["BE", "Packaging", "EE"],
            "row_chunks": 3,
        },
    }
    monkeypatch.setattr("app.services.kb_debug_service.load_preview", lambda _settings: report)

    svc = KBDebugService(debug_settings)
    out = svc.list_chunks()
    assert out["qa_areas"] == ["BE", "EE", "Packaging"]


def test_list_chunks_quote_manpower_baseline_rows(debug_settings, monkeypatch):
    report = {
        "corpus_path": str(debug_settings.validation_corpus_path),
        "target_file": "报价人力模板.xlsx",
        "file_role": "quote_manpower",
        "quote_baselines": {
            "path": "报价人力模板.xlsx",
            "detail": {
                "source_file": "报价人力模板.xlsx",
                "functions": {
                    "PM": {
                        "position_count": 2,
                        "positions": [
                            {"position": "PM", "tariff_level": "TE", "sum": 12.7, "nonzero_month_cells": 5, "sheet": "PM", "excel_row": 5},
                            {"position": "PMA", "tariff_level": "M", "sum": 6.3, "nonzero_month_cells": 3, "sheet": "PM", "excel_row": 6},
                        ],
                    },
                    "Chassis": {
                        "position_count": 1,
                        "positions": [
                            {"position": "Chassis module leader", "tariff_level": "TE", "sum": 45.0, "nonzero_month_cells": 8},
                        ],
                    },
                },
            },
        },
    }
    monkeypatch.setattr("app.services.kb_debug_service.load_preview", lambda _settings: report)

    svc = KBDebugService(debug_settings)
    out = svc.list_chunks()
    assert out["total"] == 3
    assert out["browse_mode"] == "baseline_rows"
    assert out["items"][0]["chunk_type"] == "baseline_row"
    assert out["items"][0]["chunk_chapter"] == "PM"

    detail = svc.get_chunk(out["items"][0]["chunk_id"])
    assert detail is not None
    assert detail["metadata"]["function"] == "PM"
    assert "Tariff Level:" in (detail.get("content") or "")
    assert "Sheet: PM" in (detail.get("content") or "")
    assert detail["metadata"].get("excel_row") == 5


def test_preview_and_index_with_mock_embed(debug_settings, tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    qa_src = Path(__file__).resolve().parents[1] / "backend" / "data" / "templates" / "qa_template.xlsx"
    if not qa_src.exists():
        pytest.skip("qa_template missing")
    import shutil

    shutil.copy(qa_src, corpus / "Q_A_模板.xlsx")

    svc = KBDebugService(debug_settings)

    indexed: dict[str, object] = {"chunks": 0}

    def fake_index_folder(folder, *, clear=True):
        report = svc.preview_ingest(folder)
        chunks = report.get("indexable_chunks") or []
        indexed["chunks"] = len(chunks)
        return {
            "indexed_chunks": len(chunks),
            "corpus_path": str(folder),
            "last_index_at": "2026-01-01T00:00:00Z",
            "embedding_model": debug_settings.embedding_model,
        }

    def fake_search(query, *, top_k=5, function_filter=None, doc_type_filter=None):
        return [
            {
                "chunk_id": "c1",
                "content": "sample",
                "metadata": {"doc_type": "qa"},
                "similarity_score": 0.9,
            }
        ]

    monkeypatch.setattr(svc._index, "index_corpus_folder", fake_index_folder)
    monkeypatch.setattr(svc._index, "search", fake_search)
    monkeypatch.setattr(svc._index, "indexed_count", lambda: indexed["chunks"])

    report = svc.preview_ingest(corpus)
    assert report["qa"]["row_chunks"] >= 1

    result = svc.index_corpus(corpus)
    assert result["indexed_chunks"] >= 1

    hits = svc.search("question", top_k=3)
    assert len(hits) >= 1
