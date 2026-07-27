from app.services.engagement_completeness import classify_engagement


def test_classify_complete_engagement_as_gold():
    assert classify_engagement([]) == {
        "tier": "gold",
        "indexable": True,
        "automation_impacts": [],
    }


def test_classify_rfq_only_engagement_as_indexable_copper():
    result = classify_engagement(["qa", "quote_manpower"])

    assert result["tier"] == "copper"
    assert result["indexable"] is True
    assert result["automation_impacts"] == [
        "缺 Q&A：第三期 Q&A 自动生成不可用（M4）",
        "缺人力报价 Excel：第二期报价 Excel 自动生成不可用（M3）",
    ]


def test_classify_missing_rfq_as_not_indexable():
    result = classify_engagement(["rfq"])

    assert result["tier"] == "copper"
    assert result["indexable"] is False
    assert result["automation_impacts"] == ["缺 RFQ：无法参与 RFQ 相似检索与对标"]


def test_classify_missing_metadata_as_not_indexable():
    result = classify_engagement(["metadata"])

    assert result["tier"] == "copper"
    assert result["indexable"] is False
    assert any("项目信息未齐" in item for item in result["automation_impacts"])
