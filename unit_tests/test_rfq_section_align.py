"""Unit tests for Layer-2 RFQ section alignment."""

from app.services.rfq_section_align import (
    align_dimension_to_chunks,
    align_sections_for_engagement,
    apply_section_align_to_groups,
    content_overlap_score,
    diagnose_align_miss,
    normalize_title,
    title_overlap_score,
)


def test_normalize_title_strips_numbering():
    assert normalize_title("4.1.1 前悬架开发") == "前悬架开发"
    assert normalize_title("四、工作内容") == "工作内容"


def test_title_overlap_matches_section_path():
    score = title_overlap_score(
        "前悬架开发",
        "四、工作内容 > 4.1 底盘 > 4.1.1 前悬架开发",
    )
    assert score >= 0.35


def test_align_dimension_extracts_leaf_body():
    chunks = [
        {
            "chunk_id": "c1",
            "content": "四、工作内容 > 前悬架开发\n前悬 MacPherson + 转向节数据交付",
            "metadata": {
                "section_path": "四、工作内容 > 前悬架开发",
                "chunk_chapter": "前悬架开发",
            },
        },
        {
            "chunk_id": "c2",
            "content": "四、工作内容 > 后悬架\n多连杆后悬",
            "metadata": {
                "section_path": "四、工作内容 > 后悬架",
                "chunk_chapter": "后悬架",
            },
        },
    ]
    cell = align_dimension_to_chunks(
        "前悬架开发",
        "前悬架 M1/M2 数据开发 MacPherson",
        chunks,
    )
    assert cell["value"] != "未知"
    assert "MacPherson" in cell["value"] or "前悬" in cell["value"]
    assert cell["chunk_id"] == "c1"
    assert cell["section_path"] == "四、工作内容 > 前悬架开发"


def test_align_dimension_unknown_on_mismatch():
    chunks = [
        {
            "chunk_id": "c1",
            "content": "附录 > 术语表\n缩略语说明",
            "metadata": {"section_path": "附录 > 术语表", "chunk_chapter": "术语表"},
        }
    ]
    cell = align_dimension_to_chunks("前悬架开发", "前悬架开发", chunks)
    assert cell["value"] == "未知"
    assert cell["match"] is None
    assert cell["chunk_id"] is None
    assert cell["align_status"] == "title_below_threshold"
    assert cell["align_diag"]["reason_code"] == "NO_BODY_EVIDENCE"


def test_align_via_baseline_keyword_when_title_differs():
    """Method A: dimension name misses, keyword hits section title → excerpt."""
    chunks = [
        {
            "chunk_id": "nvh1",
            "content": "4.2 噪声振动分析\n整车 NVH 目标与模态校核",
            "metadata": {
                "section_path": "4.2 噪声振动分析",
                "chunk_chapter": "噪声振动分析",
            },
        }
    ]
    # Name alone may not overlap 「噪声振动」; keyword 「NVH」 / 「噪声」 should.
    cell = align_dimension_to_chunks(
        "NVH 仿真",
        "模态与噪声",
        chunks,
        keywords=["NVH", "模态", "振动", "噪声"],
    )
    assert cell["value"] != "未知"
    assert "NVH" in cell["value"] or "模态" in cell["value"] or "噪声" in cell["value"]
    assert cell["align_diag"]["match_via"] == "keyword"
    assert cell["section_path"] == "4.2 噪声振动分析"


def test_resolve_align_keywords_prefers_item_then_index():
    from app.services.rfq_section_align import resolve_align_keywords

    item = {"name": "NVH 仿真", "dimension_id": "cae_nvh", "keywords": ["噪声"]}
    assert resolve_align_keywords(item, keyword_index={"cae_nvh": ["NVH"]}) == ["噪声"]
    item2 = {"name": "NVH 仿真", "dimension_id": "cae_nvh"}
    assert resolve_align_keywords(
        item2, keyword_index={"cae_nvh": ["NVH", "模态"]}
    ) == ["NVH", "模态"]


def test_align_diag_title_mismatch_when_body_has_terms():
    chunks = [
        {
            "chunk_id": "c1",
            "content": "总则\n本项目包含前悬架开发与转向节交付",
            "metadata": {"section_path": "1 总则", "chunk_chapter": "总则"},
        }
    ]
    diag = diagnose_align_miss("前悬架开发", "前悬架 M1", chunks, title_min=0.35)
    assert diag["reason_code"] == "TITLE_MISMATCH"
    assert diag["body_term_hits"] >= 1
    assert "标题" in diag["reason_zh"]


def test_keyword_index_from_seed_baseline():
    from pathlib import Path

    from app.config import Settings
    from app.services.dimension_baseline_service import DimensionBaselineService

    seed = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "data"
        / "config"
        / "dimension_baseline.v1.json"
    )
    if not seed.is_file():
        import pytest

        pytest.skip("seed baseline missing")
    idx = DimensionBaselineService(
        Settings(dimension_baseline_path=str(seed))
    ).keyword_index()
    assert "cae_nvh" in idx or "NVH 仿真" in idx
    kws = idx.get("cae_nvh") or idx.get("NVH 仿真") or []
    assert any("NVH" in k or "噪声" in k for k in kws)


def test_align_sections_for_engagement_coverage():
    draft = {
        "items": [
            {"name": "平台类型", "in_scope": True, "work_content": "MEB 平台"},
            {"name": "车身材料", "in_scope": True, "work_content": "全钢"},
            {"name": "内外饰范围", "in_scope": True, "work_content": "仪表板"},
        ]
    }
    chunks = [
        {
            "chunk_id": "p",
            "content": "工作内容 > 平台类型\nMEB 平台底盘",
            "metadata": {"section_path": "工作内容 > 平台类型", "chunk_chapter": "平台类型"},
        },
        {
            "chunk_id": "m",
            "content": "工作内容 > 车身材料\n全钢车身",
            "metadata": {"section_path": "工作内容 > 车身材料", "chunk_chapter": "车身材料"},
        },
    ]
    result = align_sections_for_engagement(draft, chunks)
    assert result["aligned_count"] == 2
    assert result["section_coverage"] == round(2 / 3, 3)
    assert result["dimensions"]["平台类型"]["value"] != "未知"
    assert result["dimensions"]["内外饰范围"]["value"] == "未知"


def test_apply_section_align_keeps_layer1_order_by_default():
    groups = [
        {
            "engagement_id": "eng_a",
            "project_name": "A",
            "similarity_score": 0.90,
            "metadata": {"engagement_id": "eng_a"},
            "hits": [{"content": "a", "metadata": {"engagement_id": "eng_a"}, "similarity_score": 0.9}],
        },
        {
            "engagement_id": "eng_b",
            "project_name": "B",
            "similarity_score": 0.70,
            "metadata": {"engagement_id": "eng_b"},
            "hits": [{"content": "b", "metadata": {"engagement_id": "eng_b"}, "similarity_score": 0.7}],
        },
    ]
    draft = {
        "items": [{"name": "平台类型", "in_scope": True, "work_content": "MEB 平台底盘模块"}]
    }

    def fetch(eid, _src):
        if eid == "eng_b":
            return [
                {
                    "chunk_id": "b1",
                    "content": "工作内容 > 平台类型\nMEB 平台底盘模块开发",
                    "metadata": {
                        "section_path": "工作内容 > 平台类型",
                        "chunk_chapter": "平台类型",
                    },
                }
            ]
        return [
            {
                "chunk_id": "a1",
                "content": "附录 > 其他\n无关",
                "metadata": {"section_path": "附录 > 其他", "chunk_chapter": "其他"},
            }
        ]

    ranked = apply_section_align_to_groups(
        groups, draft, fetch_chunks=fetch, top_k=2, rerank=False
    )
    assert ranked[0]["engagement_id"] == "eng_a"
    assert ranked[1]["aligned_dimensions"]["平台类型"]["value"] != "未知"


def test_content_overlap_basic():
    assert content_overlap_score("MEB 平台", "MEB 平台底盘") > 0.3
    assert content_overlap_score("", "x") == 0.0


def test_same_source_layer2_shortcircuit_sets_full_coverage_and_match():
    from app.services.rfq_section_align import apply_same_source_layer2_shortcircuit

    draft = {
        "items": [
            {"name": "仪表板", "in_scope": True, "work_content": "IP"},
            {"name": "副车架/悬置", "in_scope": True, "work_content": "副车架"},
            {"name": "NVH 仿真", "in_scope": True, "work_content": "NVH"},
        ]
    }
    groups = [
        {
            "engagement_id": "twin",
            "same_source": True,
            "section_coverage": 0.33,
            "aligned_dimensions": {
                "仪表板": {
                    "value": "重点区域…仪表板总成",
                    "match": True,
                    "section_path": "4.1.7.3",
                    "content_score": 0.5,
                },
                "副车架/悬置": {
                    "value": "重点区域…底盘悬置",
                    "match": None,
                    "section_path": "4.1.7.3",
                    "content_score": 0.1,
                },
            },
            "metadata": {"engagement_id": "twin", "same_source": True},
            "hits": [],
        },
        {
            "engagement_id": "other",
            "same_source": False,
            "section_coverage": 0.33,
            "aligned_dimensions": {
                "仪表板": {"value": "摘录", "match": None, "content_score": 0.2},
            },
            "metadata": {"engagement_id": "other"},
            "hits": [],
        },
    ]
    out = apply_same_source_layer2_shortcircuit(groups, draft)
    twin = out[0]
    assert twin["section_coverage"] == 1.0
    assert twin["section_content_mean"] == 1.0
    assert twin["aligned_dimensions"]["仪表板"]["match"] is True
    assert twin["aligned_dimensions"]["副车架/悬置"]["match"] is True
    assert "底盘悬置" in twin["aligned_dimensions"]["副车架/悬置"]["value"]
    assert twin["aligned_dimensions"]["NVH 仿真"]["match"] is True
    # No chapter excerpt → do not claim file identity in the cell
    assert "同源" not in twin["aligned_dimensions"]["NVH 仿真"]["value"]
    assert "一致" not in twin["aligned_dimensions"]["NVH 仿真"]["value"]
    assert twin["aligned_dimensions"]["NVH 仿真"]["value"] == "未匹配到对应章节"
    nvh_diag = twin["aligned_dimensions"]["NVH 仿真"]["align_diag"]
    assert nvh_diag["reason_code"] in {"TITLE_MISMATCH", "NO_BODY_EVIDENCE", "EMPTY_DOC"}
    assert nvh_diag.get("reason_zh")

    other = out[1]
    assert other["section_coverage"] == 0.33
    assert other["aligned_dimensions"]["仪表板"]["match"] is None


def test_same_source_soft_refill_prefers_chapter_excerpt():
    from app.services.rfq_section_align import apply_same_source_layer2_shortcircuit

    draft = {
        "items": [
            {"name": "白车身结构", "in_scope": True, "work_content": "白车身"},
        ]
    }
    chunks = [
        {
            "chunk_id": "c1",
            "content": "4.1.2.4 车身/车身附件各个系统竞品对比与结构方案",
            "metadata": {
                "section_path": "4.1.2.4 白车身结构",
                "chunk_chapter": "白车身结构",
            },
        }
    ]
    groups = [
        {
            "engagement_id": "twin",
            "same_source": True,
            "aligned_dimensions": {
                "白车身结构": {"value": "未知", "match": None},
            },
            "metadata": {"engagement_id": "twin", "same_source": True},
            "hits": [],
        }
    ]
    out = apply_same_source_layer2_shortcircuit(
        groups,
        draft,
        fetch_chunks=lambda *_a, **_k: chunks,
    )
    value = out[0]["aligned_dimensions"]["白车身结构"]["value"]
    assert "同源" not in value
    assert "车身" in value or "白车身" in value
    assert out[0]["aligned_dimensions"]["白车身结构"]["match"] is True