import json

import pytest

from app.config import Settings
from app.services.rag_service import (
    RAGProductionError,
    RAGService,
    compute_function_coverage,
    group_hits_by_engagement,
)


def test_search_similar_projects_applies_structured_rerank(monkeypatch):
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))

    def fake_grouped(*_args, **_kwargs):
        return [
            {
                "engagement_id": "eng_a",
                "project_name": "MEB Chassis",
                "similarity_score": 0.70,
                "metadata": {
                    "engagement_id": "eng_a",
                    "project_name": "MEB Chassis",
                    "customer": "HOZON",
                    "functions": ["Chassis", "PM"],
                    "doc_type": "rfq",
                },
                "hits": [
                    {
                        "content": "chassis",
                        "similarity_score": 0.70,
                        "metadata": {
                            "engagement_id": "eng_a",
                            "project_name": "MEB Chassis",
                            "customer": "HOZON",
                            "functions": ["Chassis", "PM"],
                            "section_path": "工作内容及要求 > 底盘",
                            "doc_type": "rfq",
                        },
                    }
                ],
            },
            {
                "engagement_id": "eng_b",
                "project_name": "Interior Only",
                "similarity_score": 0.95,
                "metadata": {
                    "engagement_id": "eng_b",
                    "project_name": "Interior Only",
                    "functions": ["Interior"],
                    "doc_type": "rfq",
                },
                "hits": [
                    {
                        "content": "interior",
                        "similarity_score": 0.95,
                        "metadata": {
                            "engagement_id": "eng_b",
                            "project_name": "Interior Only",
                            "functions": ["Interior"],
                            "section_path": "内饰",
                            "doc_type": "rfq",
                        },
                    }
                ],
            },
        ]

    monkeypatch.setattr(rag, "search_grouped", fake_grouped)
    hits = rag.search_similar_projects(
        "ignored",
        top_k=1,
        rfq_modules={
            "project_name": "MEB Chassis",
            "customer": "HOZON",
            "functions_in_scope": ["Chassis", "PM"],
            "development_scope": [{"title": "工作内容及要求"}],
        },
    )
    assert len(hits) == 1
    assert hits[0]["metadata"]["engagement_id"] == "eng_a"
    assert "structured_score" in hits[0]["metadata"]
    assert "vector_score" in hits[0]["metadata"]


def test_search_similar_projects_layer2_fills_dimensions(monkeypatch):
    rag = RAGService(Settings(mock_rag=False, knowledge_base_path="./data/knowledge_base"))

    def fake_grouped(*_args, **_kwargs):
        return [
            {
                "engagement_id": "eng_a",
                "project_name": "MEB Chassis",
                "similarity_score": 0.80,
                "source_doc": "a/rfq.docx",
                "metadata": {
                    "engagement_id": "eng_a",
                    "project_name": "MEB Chassis",
                    "functions": ["Chassis"],
                    "doc_type": "rfq",
                    "source_doc": "a/rfq.docx",
                },
                "hits": [
                    {
                        "content": "hit",
                        "similarity_score": 0.80,
                        "metadata": {
                            "engagement_id": "eng_a",
                            "project_name": "MEB Chassis",
                            "functions": ["Chassis"],
                            "doc_type": "rfq",
                            "source_doc": "a/rfq.docx",
                            "section_path": "工作内容 > 平台类型",
                        },
                    }
                ],
            }
        ]

    def fake_fetch(_engagement_id, _source_doc):
        return [
            {
                "chunk_id": "a::platform",
                "content": "工作内容 > 平台类型\nMEB 平台底盘模块开发",
                "metadata": {
                    "engagement_id": "eng_a",
                    "section_path": "工作内容 > 平台类型",
                    "chunk_chapter": "平台类型",
                    "doc_type": "rfq",
                },
            }
        ]

    monkeypatch.setattr(rag, "search_grouped", fake_grouped)
    monkeypatch.setattr(rag, "_fetch_engagement_chunks", fake_fetch)
    draft = {
        "items": [
            {"name": "平台类型", "in_scope": True, "work_content": "MEB 平台底盘"},
            {"name": "缺失维度", "in_scope": True, "work_content": "无对应章节"},
        ]
    }
    hits = rag.search_similar_projects(
        "ignored",
        top_k=1,
        rfq_modules={"project_name": "MEB Chassis", "functions_in_scope": ["Chassis"]},
        draft=draft,
    )
    assert len(hits) == 1
    dims = hits[0]["metadata"]["dimensions"]
    assert dims["平台类型"]["value"] != "未知"
    assert dims["平台类型"]["section_path"]
    assert dims["缺失维度"]["value"] == "未知"
    assert "section_coverage" in hits[0]["metadata"]

    table = rag.build_comparison_table_from_draft(
        {"functions_in_scope": ["Chassis"]},
        hits,
        draft,
    )
    project = table["projects"][0]
    assert project["dimensions"]["平台类型"]["value"] != "未知"
    history_vals = [
        cell["value"]
        for row in table["matrix_rows"]
        if row["dimension"] == "平台类型"
        for cell in row["history"]
    ]
    assert history_vals and history_vals[0] != "未知"
    assert table["matrix_rows"][0]["history"][0].get("section_path")


def test_knowledge_and_rfq_share_same_search_pipeline():
    """Without structured rerank, RFQ hits match grouped hybrid_top_m + rfq filter."""
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    query = "MEB chassis suspension"
    rfq_hits = rag.search_similar_projects(query, top_k=3, doc_type_filter=["rfq"])
    groups = rag.search_grouped(
        query,
        top_k=3,
        doc_type_filter=["rfq"],
        citations_per_group=5,
        score_mode="hybrid_top_m",
        score_top_m=3,
    )
    assert [g["hits"][0]["metadata"]["engagement_id"] for g in groups] == [
        (h.get("metadata") or {}).get("engagement_id") for h in rfq_hits
    ]
    assert rfq_hits[0]["similarity_score"] == groups[0]["similarity_score"]


def test_group_hits_mean_top_m_softens_single_chunk_spike():
    hits = [
        {
            "content": "a",
            "similarity_score": 0.99,
            "metadata": {"engagement_id": "eng_a", "project_name": "A", "doc_type": "rfq"},
        },
        {
            "content": "b",
            "similarity_score": 0.50,
            "metadata": {"engagement_id": "eng_a", "project_name": "A", "doc_type": "rfq"},
        },
        {
            "content": "c",
            "similarity_score": 0.50,
            "metadata": {"engagement_id": "eng_a", "project_name": "A", "doc_type": "rfq"},
        },
        {
            "content": "d",
            "similarity_score": 0.80,
            "metadata": {"engagement_id": "eng_b", "project_name": "B", "doc_type": "rfq"},
        },
        {
            "content": "e",
            "similarity_score": 0.79,
            "metadata": {"engagement_id": "eng_b", "project_name": "B", "doc_type": "rfq"},
        },
        {
            "content": "f",
            "similarity_score": 0.78,
            "metadata": {"engagement_id": "eng_b", "project_name": "B", "doc_type": "rfq"},
        },
    ]
    by_max = group_hits_by_engagement(hits, top_k=2, score_mode="max")
    by_mean = group_hits_by_engagement(hits, top_k=2, score_mode="mean_top_m", score_top_m=3)
    assert by_max[0]["engagement_id"] == "eng_a"
    assert by_mean[0]["engagement_id"] == "eng_b"
    assert by_mean[0]["similarity_score"] == round((0.80 + 0.79 + 0.78) / 3, 3)


def test_group_hits_by_engagement_dedupes_same_project():
    hits = [
        {
            "content": "a",
            "similarity_score": 0.9,
            "metadata": {
                "engagement_id": "eng_a",
                "project_name": "A",
                "source_doc": "a/rfq.docx",
                "doc_type": "rfq",
                "functions": ["Chassis"],
            },
        },
        {
            "content": "b",
            "similarity_score": 0.8,
            "metadata": {
                "engagement_id": "eng_a",
                "project_name": "A",
                "source_doc": "a/rfq.docx",
                "doc_type": "rfq",
                "functions": ["Chassis"],
                "section_path": "四、工作内容 > 4.1",
            },
        },
        {
            "content": "c",
            "similarity_score": 0.7,
            "metadata": {
                "engagement_id": "eng_b",
                "project_name": "B",
                "source_doc": "b/rfq.docx",
                "doc_type": "rfq",
                "functions": ["PM"],
            },
        },
    ]
    groups = group_hits_by_engagement(hits, top_k=5, citations_per_group=3)
    assert len(groups) == 2
    assert groups[0]["engagement_id"] == "eng_a"
    assert groups[0]["similarity_score"] == 0.9
    assert len(groups[0]["hits"]) == 2
    assert groups[1]["engagement_id"] == "eng_b"


def test_projects_from_hits_dedupes_engagement():
    rag = RAGService(Settings(mock_rag=False, knowledge_base_path="./data/knowledge_base"))
    hits = [
        {
            "content": "one",
            "similarity_score": 0.91,
            "metadata": {
                "engagement_id": "eng_a",
                "project_name": "A",
                "source_doc": "a/rfq.docx",
                "functions": ["Chassis"],
            },
        },
        {
            "content": "two",
            "similarity_score": 0.88,
            "metadata": {
                "engagement_id": "eng_a",
                "project_name": "A",
                "source_doc": "a/rfq.docx",
                "functions": ["Chassis"],
            },
        },
        {
            "content": "three",
            "similarity_score": 0.7,
            "metadata": {
                "engagement_id": "eng_b",
                "project_name": "B",
                "source_doc": "b/rfq.docx",
                "functions": ["PM"],
            },
        },
    ]
    projects = rag._projects_from_hits(hits)
    assert len(projects) == 2
    assert projects[0]["engagement_id"] == "eng_a"
    assert projects[1]["engagement_id"] == "eng_b"


def test_projects_from_hits_prefers_live_manifest_vehicle_model(tmp_path):
    import json

    eng = tmp_path / "test"
    eng.mkdir()
    (eng / "manifest.json").write_text(
        json.dumps(
            {
                "engagement_id": "test",
                "project_name": "上海通用汽车",
                "customer": "上海通用汽车",
                "vehicle_model": "新能源纯电",
                "year": 2026,
                "functions": ["PM"],
                "documents": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rag = RAGService(Settings(mock_rag=False, knowledge_base_path=str(tmp_path)))
    projects = rag._projects_from_hits(
        [
            {
                "content": "stale",
                "similarity_score": 1.0,
                "metadata": {
                    "engagement_id": "test",
                    "project_name": "上海通用汽车",
                    "customer": "上海通用",
                    "vehicle_model": "",
                    "source_doc": "test/rfq.docx",
                },
            }
        ]
    )
    assert projects[0]["customer"] == "上海通用汽车"
    assert projects[0]["vehicle_model"] == "新能源纯电"


def test_enrich_comparison_projects_overlays_live_fields(tmp_path):
    import json

    eng = tmp_path / "test"
    eng.mkdir()
    (eng / "manifest.json").write_text(
        json.dumps(
            {
                "engagement_id": "test",
                "project_name": "上海通用汽车",
                "customer": "上海通用汽车",
                "vehicle_model": "新能源纯电",
                "year": 2026,
                "functions": ["PM"],
                "documents": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rag = RAGService(Settings(mock_rag=False, knowledge_base_path=str(tmp_path)))
    enriched = rag.enrich_comparison_projects(
        [
            {
                "engagement_id": "test",
                "project_name": "上海通用汽车",
                "customer": "上海通用",
                "vehicle_model": "",
            }
        ]
    )
    assert enriched[0]["customer"] == "上海通用汽车"
    assert enriched[0]["vehicle_model"] == "新能源纯电"


def test_mock_search_returns_top_k():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    results = rag.search_similar_projects("MEB chassis", top_k=2)
    assert len(results) == 2
    assert results[0]["similarity_score"] >= results[1]["similarity_score"]


def test_mock_search_hit_schema():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    hit = rag.search_similar_projects("chassis", top_k=1)[0]
    assert "content" in hit
    assert "similarity_score" in hit
    meta = hit["metadata"]
    assert "project_name" in meta
    assert "source_doc" in meta
    assert "functions" in meta


def test_search_function_filter():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    results = rag.search_similar_projects("chassis", top_k=5, function_filter=["PM"])
    assert all("PM" in (h.get("metadata") or {}).get("functions", []) for h in results)


def test_compute_function_coverage_uncovered():
    hits = [
        {"metadata": {"functions": ["PM", "Chassis"]}},
        {"metadata": {"functions": ["Chassis"]}},
    ]
    coverage = compute_function_coverage(["PM", "Chassis", "BIW"], hits)
    assert coverage["uncovered"] == ["BIW"]
    assert "PM" in coverage["covered"]
    assert "Chassis" in coverage["covered"]


def test_build_comparison_table_has_confidence_and_coverage():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    rfq_data = {"project_name": "test", "functions_in_scope": ["PM", "Chassis", "BIW"]}
    docs = rag.search_similar_projects("chassis", top_k=3)
    table = rag.build_comparison_table(rfq_data, docs)
    assert table["overall_confidence"] in {"高", "中", "低"}
    assert len(table["projects"]) >= 1
    assert "matrix_rows" in table
    assert len(table["matrix_rows"]) >= 5
    assert "function_coverage" in table
    assert "BIW" in table["function_coverage"]["uncovered"]
    assert table["insufficient_evidence"] is False


def test_build_comparison_table_propagates_engagement_id():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    rfq_data = {"project_name": "test", "functions_in_scope": ["PM", "Chassis"]}
    docs = rag.search_similar_projects("chassis", top_k=1)
    table = rag.build_comparison_table(rfq_data, docs)
    assert table["projects"][0]["engagement_id"] == "mock_project_1"


def test_group_hybrid_score_blends_max_and_mean():
    from app.services.rag_service import _group_similarity_score

    hits = [
        {"similarity_score": 0.9},
        {"similarity_score": 0.6},
        {"similarity_score": 0.3},
    ]
    hybrid = _group_similarity_score(hits, score_mode="hybrid_top_m", score_top_m=3)
    mean = (0.9 + 0.6 + 0.3) / 3
    assert hybrid == pytest.approx(0.7 * 0.9 + 0.3 * mean)


def test_same_source_boost_pins_matching_engagement(tmp_path, monkeypatch):
    kb = tmp_path / "kb"
    eng = kb / "twin"
    eng.mkdir(parents=True)
    rfq = eng / "RFQ.docx"
    rfq.write_bytes(b"identical-rfq-bytes")
    (eng / "manifest.json").write_text(
        json.dumps(
            {
                "engagement_id": "twin",
                "project_name": "Twin Project",
                "documents": [{"path": "RFQ.docx", "doc_type": "rfq"}],
            }
        ),
        encoding="utf-8",
    )
    upload = tmp_path / "upload.doc"
    upload.write_bytes(b"identical-rfq-bytes")

    rag = RAGService(Settings(mock_rag=False, knowledge_base_path=str(kb)))
    monkeypatch.setattr(
        rag,
        "search_grouped",
        lambda *a, **k: [
            {
                "engagement_id": "other",
                "project_name": "Other",
                "similarity_score": 0.7,
                "vector_score": 0.7,
                "metadata": {"engagement_id": "other", "project_name": "Other"},
                "hits": [
                    {
                        "content": "x",
                        "similarity_score": 0.7,
                        "metadata": {"engagement_id": "other"},
                    }
                ],
            }
        ],
    )
    hits = rag.search_similar_projects(
        "query",
        top_k=3,
        source_file_path=str(upload),
    )
    assert hits[0]["metadata"]["same_source"] is True
    assert hits[0]["similarity_score"] == 1.0
    assert hits[0]["metadata"]["engagement_id"] == "twin"


def test_same_source_text_fingerprint_detects_ole_resave(tmp_path, monkeypatch):
    """Body-identical .doc twins with different bytes still count as same-source."""
    from app.services import rag_service as rag_mod

    kb = tmp_path / "kb"
    eng = kb / "test"
    eng.mkdir(parents=True)
    kb_rfq = eng / "RFQ.doc"
    kb_rfq.write_bytes(b"ole-bytes-version-a" + b"\x00" * 20)
    (eng / "manifest.json").write_text(
        json.dumps(
            {
                "engagement_id": "test",
                "project_name": "Test Twin",
                "documents": [{"path": "RFQ.doc", "doc_type": "rfq"}],
            }
        ),
        encoding="utf-8",
    )
    upload = tmp_path / "upload.doc"
    upload.write_bytes(b"ole-bytes-version-b" + b"\xff" * 24)
    assert kb_rfq.read_bytes() != upload.read_bytes()

    def fake_fp(path):
        # Same normalized body regardless of which twin file.
        p = str(path)
        if p.endswith("RFQ.doc") or p.endswith("upload.doc"):
            return "same-text-fingerprint"
        return None

    monkeypatch.setattr(rag_mod, "_rfq_text_fingerprint", fake_fp)

    rag = RAGService(Settings(mock_rag=False, knowledge_base_path=str(kb)))
    monkeypatch.setattr(
        rag,
        "search_grouped",
        lambda *a, **k: [
            {
                "engagement_id": "test",
                "project_name": "Test Twin",
                "similarity_score": 0.55,
                "vector_score": 0.55,
                "metadata": {"engagement_id": "test", "project_name": "Test Twin"},
                "hits": [
                    {
                        "content": "chassis",
                        "similarity_score": 0.55,
                        "metadata": {"engagement_id": "test"},
                    }
                ],
            }
        ],
    )
    draft = {
        "items": [
            {"name": "转向系统", "in_scope": True, "work_content": "转向"},
            {"name": "制动系统", "in_scope": True, "work_content": "制动"},
        ]
    }
    hits = rag.search_similar_projects(
        "query",
        top_k=3,
        rfq_modules={"functions_in_scope": ["Chassis"]},
        draft=draft,
        source_file_path=str(upload),
    )
    assert hits[0]["metadata"]["engagement_id"] == "test"
    assert hits[0]["metadata"]["same_source"] is True
    dims = hits[0]["metadata"]["dimensions"]
    assert dims["转向系统"]["value"] != "未知"
    assert dims["制动系统"]["same_source"] is True


def test_insufficient_evidence_uses_vector_score_not_only_fused():
    rag = RAGService(
        Settings(mock_rag=False, rag_similarity_threshold=0.55, knowledge_base_path="./data/knowledge_base")
    )
    # Fused score below threshold, vector recall above → still sufficient.
    assert (
        rag.is_insufficient_evidence(
            [
                {
                    "similarity_score": 0.40,
                    "metadata": {"vector_score": 0.62},
                }
            ]
        )
        is False
    )
    assert (
        rag.is_insufficient_evidence(
            [
                {
                    "similarity_score": 0.40,
                    "metadata": {"vector_score": 0.40},
                }
            ]
        )
        is True
    )
    assert (
        rag.is_insufficient_evidence(
            [{"similarity_score": 0.2, "metadata": {"same_source": True}}]
        )
        is False
    )


def test_build_comparison_table_insufficient_evidence_no_mock_projects():
    rag = RAGService(
        Settings(mock_rag=False, rag_similarity_threshold=0.55, knowledge_base_path="./data/knowledge_base")
    )
    rfq_data = {"project_name": "test", "functions_in_scope": ["PM"]}
    table = rag.build_comparison_table(rfq_data, [])
    assert table["insufficient_evidence"] is True
    assert table["projects"] == []
    assert "暂无足够历史项目" in table["recommendation"]


def test_search_doc_type_filter():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    results = rag.search_similar_projects("chassis", top_k=5, doc_type_filter=["summary"])
    assert all((h.get("metadata") or {}).get("doc_type") == "summary" for h in results)


def test_search_delegates_to_knowledge_index_service(monkeypatch, tmp_path):
    """SPK-K03: production RAG uses KnowledgeIndexService.search with same filters."""
    kb = tmp_path / "kb"
    kb.mkdir()
    rag = RAGService(
        Settings(
            mock_rag=False,
            knowledge_base_path=str(kb),
            knowledge_vector_namespace="production",
        )
    )
    calls: list[tuple] = []

    class FakeIndex:
        namespace = "production"

        def search(
            self,
            query: str,
            *,
            top_k: int = 5,
            function_filter: list[str] | None = None,
            doc_type_filter: list[str] | None = None,
            request_type: str = "query",
            cancel_check=None,
        ):
            calls.append((query, top_k, function_filter, doc_type_filter, request_type))
            return [
                {
                    "content": "scope text",
                    "similarity_score": 0.91,
                    "metadata": {
                        "doc_type": "rfq",
                        "project_name": "Demo",
                        "source_doc": "knowledge_base/eng/rfq.docx",
                        "functions": ["Chassis"],
                    },
                }
            ]

    monkeypatch.setattr(
        "app.services.knowledge_index_service.KnowledgeIndexService",
        lambda _settings, namespace=None: FakeIndex(),
    )
    hits = rag.search_similar_projects(
        "MEB chassis",
        top_k=3,
        function_filter=["Chassis"],
        doc_type_filter=["rfq"],
    )
    assert len(calls) == 1
    assert calls[0] == ("MEB chassis", 3, ["Chassis"], ["rfq"], "query")
    assert hits[0]["similarity_score"] == 0.91
    assert hits[0]["metadata"]["doc_type"] == "rfq"


def test_real_search_empty_returns_no_mock_fallback(monkeypatch, tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    chroma = tmp_path / "chroma"
    rag = RAGService(
        Settings(mock_rag=False, knowledge_base_path=str(kb), chroma_path=str(chroma))
    )

    class FakeIndex:
        def search(
            self,
            query: str,
            top_k: int = 5,
            function_filter: list[str] | None = None,
            doc_type_filter: list[str] | None = None,
            request_type: str = "query",
            cancel_check=None,
        ):
            return []

    monkeypatch.setattr(
        "app.services.knowledge_index_service.KnowledgeIndexService",
        lambda _settings, namespace=None: FakeIndex(),
    )
    assert rag.search_similar_projects("MEB chassis", top_k=3) == []


def test_list_documents_mock():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    docs = rag.list_documents()
    assert len(docs) == 3
    statuses = {d["status"] for d in docs}
    assert statuses == {"indexed", "pending", "failed"}


def test_import_skips_unchanged_hash(tmp_path):
    kb = tmp_path / "kb" / "proj_a"
    kb.mkdir(parents=True)
    doc = kb / "rfq.docx"
    doc.write_bytes(b"fake docx content for hash test")

    rag = RAGService(
        Settings(mock_rag=True, knowledge_base_path=str(tmp_path / "kb"))
    )
    first = rag.import_documents()
    assert first["new_documents"] == 1
    assert first["skipped"] == 0

    second = rag.import_documents()
    assert second["new_documents"] == 1
    assert second["new_chunks"] == 10


def test_import_documents_production_raises():
    rag = RAGService(
        Settings(mock_rag=False, knowledge_base_path="./data/knowledge_base")
    )
    with pytest.raises(RAGProductionError, match="reindex"):
        rag.import_documents()


def test_get_stats_production_uses_pgvector(monkeypatch, tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    rag = RAGService(
        Settings(mock_rag=False, knowledge_base_path=str(kb), knowledge_vector_namespace="prod")
    )

    class FakeIndex:
        namespace = "prod"

        def indexed_count(self):
            return 42

        def last_index_state(self):
            return {"last_index_at": "2026-01-01T00:00:00Z", "embedding_model": "nomic-embed-text"}

        def list_indexed_source_docs(self):
            return set()

    monkeypatch.setattr(rag, "_index_service", lambda: FakeIndex())
    stats = rag.get_stats()
    assert stats["vector_store"] == "pgvector"
    assert stats["total_chunks"] == 42
    assert stats["mock_rag"] is False


def test_list_documents_production_from_manifest(tmp_path, monkeypatch):
    kb = tmp_path / "kb" / "eng_001"
    kb.mkdir(parents=True)
    (kb / "rfq.docx").write_bytes(b"rfq")
    (kb / "manifest.json").write_text(
        '{"engagement_id":"eng_001","project_name":"Demo Project","documents":[{"path":"rfq.docx","doc_type":"rfq"}]}',
        encoding="utf-8",
    )

    rag = RAGService(Settings(mock_rag=False, knowledge_base_path=str(tmp_path / "kb")))

    class FakeIndex:
        def list_indexed_source_docs(self):
            return {"knowledge_base/eng_001/rfq.docx"}

    monkeypatch.setattr(rag, "_index_service", lambda: FakeIndex())
    docs = rag.list_documents()
    assert len(docs) == 1
    assert docs[0]["status"] == "indexed"
    assert docs[0]["engagement_id"] == "eng_001"
    assert docs[0]["doc_type"] == "rfq"
    assert docs[0].get("metadata_summary") is None


def test_list_documents_matches_legacy_basename_source_doc(tmp_path, monkeypatch):
    """Ingest historically stored basename-only source_doc; UI must still show indexed."""
    kb = tmp_path / "kb" / "test"
    kb.mkdir(parents=True)
    (kb / "RFQ_客户A.doc").write_bytes(b"rfq")
    (kb / "Q_A_模板.xlsx").write_bytes(b"qa")
    (kb / "报价人力模板.xlsx").write_bytes(b"quote")
    (kb / "manifest.json").write_text(
        json.dumps(
            {
                "engagement_id": "test",
                "project_name": "Test",
                "documents": [
                    {"path": "RFQ_客户A.doc", "doc_type": "rfq"},
                    {"path": "Q_A_模板.xlsx", "doc_type": "qa"},
                    {"path": "报价人力模板.xlsx", "doc_type": "quote_manpower"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    baselines = tmp_path / "manpower_baselines.json"
    baselines.write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "engagement_id": "test",
                        "source_doc": "knowledge_base/test/报价人力模板.xlsx",
                        "functions": {},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rag = RAGService(
        Settings(
            mock_rag=False,
            knowledge_base_path=str(tmp_path / "kb"),
            manpower_baselines_path=str(baselines),
        )
    )

    class FakeIndex:
        def list_indexed_source_docs_by_engagement(self):
            return {"test": {"RFQ_客户A.doc", "Q_A_模板.xlsx"}}

        def list_indexed_source_docs(self):
            return {"RFQ_客户A.doc", "Q_A_模板.xlsx"}

    monkeypatch.setattr(rag, "_index_service", lambda: FakeIndex())
    docs = {d["path"]: d for d in rag.list_documents()}
    assert docs["test/RFQ_客户A.doc"]["status"] == "indexed"
    assert docs["test/Q_A_模板.xlsx"]["status"] == "indexed"
    assert docs["test/报价人力模板.xlsx"]["status"] == "indexed"


def test_mock_stats_includes_function_coverage():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    stats = rag.get_stats()
    assert stats["total_documents"] > 0
    assert "function_coverage" in stats
    assert stats["function_coverage"]["Chassis"] >= 0.9
