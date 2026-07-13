from app.services.rfq_structured_similarity import (
    fuse_similarity_scores,
    jaccard,
    rerank_similar_groups,
    structured_similarity_score,
)


def test_jaccard_basic():
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3
    assert jaccard(set(), {"a"}) == 0.0


def test_structured_score_prefers_matching_functions_and_scope():
    current = {
        "project_name": "客户A底盘项目",
        "customer": "客户A",
        "platform_type": "MEB",
        "functions_in_scope": ["Chassis", "PM"],
        "development_scope": [{"title": "工作内容及要求"}, {"title": "整车总布置开发"}],
    }
    strong = {
        "project_name": "客户A底盘项目 2023",
        "customer": "客户A",
        "functions": ["Chassis", "PM"],
    }
    weak = {
        "project_name": "内饰改款",
        "customer": "其它",
        "functions": ["Interior"],
    }
    strong_score = structured_similarity_score(
        current,
        strong,
        section_paths=["工作内容及要求 > 整车总布置开发 > 4.1"],
    )
    weak_score = structured_similarity_score(
        current,
        weak,
        section_paths=["内外饰要求"],
    )
    assert strong_score > weak_score
    assert strong_score >= 0.5


def test_fuse_and_rerank_can_reorder_by_structured():
    groups = [
        {
            "engagement_id": "eng_weak_vec_strong_struct",
            "project_name": "MEB Chassis",
            "similarity_score": 0.70,
            "metadata": {
                "engagement_id": "eng_weak_vec_strong_struct",
                "project_name": "MEB Chassis",
                "customer": "HOZON",
                "functions": ["Chassis", "PM"],
            },
            "hits": [
                {
                    "similarity_score": 0.70,
                    "metadata": {
                        "section_path": "工作内容及要求 > 底盘开发",
                        "functions": ["Chassis", "PM"],
                        "project_name": "MEB Chassis",
                        "customer": "HOZON",
                    },
                }
            ],
        },
        {
            "engagement_id": "eng_strong_vec_weak_struct",
            "project_name": "Random Interior",
            "similarity_score": 0.92,
            "metadata": {
                "engagement_id": "eng_strong_vec_weak_struct",
                "project_name": "Random Interior",
                "customer": "Other",
                "functions": ["Interior"],
            },
            "hits": [
                {
                    "similarity_score": 0.92,
                    "metadata": {
                        "section_path": "内饰造型",
                        "functions": ["Interior"],
                        "project_name": "Random Interior",
                    },
                }
            ],
        },
    ]
    current = {
        "project_name": "MEB Chassis",
        "customer": "HOZON",
        "platform_type": "MEB",
        "functions_in_scope": ["Chassis", "PM"],
        "development_scope": [{"title": "工作内容及要求"}, {"title": "底盘开发"}],
    }
    # Pure vector would keep Interior first; fusion should prefer Chassis.
    assert groups[0]["similarity_score"] < groups[1]["similarity_score"]
    ranked = rerank_similar_groups(groups, current, top_k=2, vector_weight=0.55)
    assert ranked[0]["engagement_id"] == "eng_weak_vec_strong_struct"
    assert ranked[0]["structured_score"] > ranked[1]["structured_score"]
    assert fuse_similarity_scores(0.9, 0.1, vector_weight=0.65) == round(
        0.65 * 0.9 + 0.35 * 0.1, 3
    )
