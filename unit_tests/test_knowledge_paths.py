"""Unit tests for knowledge source_doc path helpers."""

from app.utils.knowledge_paths import (
    canonical_knowledge_source_doc,
    is_document_source_indexed,
    source_doc_aliases,
)


def test_canonical_knowledge_source_doc():
    assert canonical_knowledge_source_doc("test", "RFQ_客户A.doc") == "knowledge_base/test/RFQ_客户A.doc"
    assert (
        canonical_knowledge_source_doc("test", "knowledge_base/test/RFQ.doc")
        == "knowledge_base/test/RFQ.doc"
    )


def test_source_doc_aliases_include_basename_and_relative():
    aliases = source_doc_aliases("knowledge_base/test/RFQ_客户A.doc")
    assert "knowledge_base/test/RFQ_客户A.doc" in aliases
    assert "test/RFQ_客户A.doc" in aliases
    assert "RFQ_客户A.doc" in aliases


def test_is_document_source_indexed_matches_legacy_basename():
    indexed = {"RFQ_客户A.doc", "Q_A_模板.xlsx"}
    assert is_document_source_indexed(indexed, "test", "RFQ_客户A.doc") is True
    assert is_document_source_indexed(indexed, "test", "Q_A_模板.xlsx") is True
    assert is_document_source_indexed(indexed, "test", "报价人力模板.xlsx") is False


def test_is_document_source_indexed_matches_canonical():
    indexed = {"knowledge_base/test/RFQ_客户A.doc"}
    assert is_document_source_indexed(indexed, "test", "RFQ_客户A.doc") is True
