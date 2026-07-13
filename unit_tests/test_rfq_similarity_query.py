from app.services.rfq_similarity_query import build_rfq_similarity_query


def test_build_query_includes_scope_and_in_scope_dimensions():
    query = build_rfq_similarity_query(
        {
            "project_name": "客户A整车项目",
            "customer": "客户A",
            "platform_type": "MEB",
            "functions_in_scope": ["Chassis", "PM"],
            "development_scope": [
                {"id": "4.1", "title": "工作内容及要求"},
                {"id": "4.1.1", "title": "整车总布置开发"},
            ],
        },
        draft={
            "items": [
                {
                    "name": "前后悬架系统设计",
                    "work_content": "MacPherson + 多连杆",
                    "in_scope": True,
                },
                {"name": "内饰", "work_content": "—", "in_scope": False},
            ]
        },
        file_name="RFQ_客户A.doc",
    )
    assert "客户A整车项目" in query
    assert "工作内容及要求" in query
    assert "整车总布置开发" in query
    assert "前后悬架系统设计" in query
    assert "MacPherson + 多连杆" in query
    assert "内饰" not in query


def test_build_query_falls_back_to_file_stem_when_name_unknown():
    query = build_rfq_similarity_query(
        {"project_name": "未知", "functions_in_scope": ["Chassis"]},
        file_name="RFQ_template.doc",
    )
    assert "RFQ_template" in query
    assert "Chassis" in query
    assert "未知" not in query


def test_build_query_dedupes_and_respects_max_chars():
    query = build_rfq_similarity_query(
        {
            "project_name": "Same",
            "customer": "Same",
            "development_scope": [{"title": "Same"}],
        },
        max_chars=20,
    )
    assert query.count("Same") == 1
    assert len(query) <= 20
