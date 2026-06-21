from app.services.comparison_service import build_comparison_matrix
from app.services.mock_data import MOCK_COMPARISON_TABLE, MOCK_RFQ_PARSE_RESULT


def test_build_matrix_has_new_project_column():
    rfq = dict(MOCK_RFQ_PARSE_RESULT)
    rfq["new_project_profile"] = {"平台类型": "MEB", "车身材料": "全钢", "仿真类型": "正面", "内外饰范围": "Chassis", "交付物数量": "5项"}
    matrix = build_comparison_matrix(rfq, MOCK_COMPARISON_TABLE["projects"])
    assert matrix["new_project_requirements"]["平台类型"] == "MEB"
    assert len(matrix["matrix_rows"]) >= 5
    first = matrix["matrix_rows"][0]
    assert first["dimension"] == "平台类型"
    assert first["new_project"] == "MEB"
    assert len(first["history"]) == 3


def test_matrix_includes_summary_and_man_days_rows():
    matrix = build_comparison_matrix(MOCK_RFQ_PARSE_RESULT, MOCK_COMPARISON_TABLE["projects"])
    dimensions = [r["dimension"] for r in matrix["matrix_rows"]]
    assert "技术差异总结" in dimensions
    assert "实际人天" in dimensions
    assert "偏差率（估→实）" in dimensions
