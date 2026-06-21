import pytest

from app.services.rag_service import calculate_overall_confidence


@pytest.mark.parametrize(
    "scores,expected",
    [
        ([0.92, 0.78, 0.71], "高"),
        ([0.80, 0.75], "中"),
        ([0.65], "低"),
        ([], "低"),
    ],
)
def test_calculate_overall_confidence(scores, expected):
    assert calculate_overall_confidence(scores) == expected
