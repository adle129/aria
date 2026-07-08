import pytest
from pydantic import ValidationError

from app.schemas.common import ApiResponse, HealthResponse


def test_health_response_valid():
    data = HealthResponse(
        status="ok",
        version="1.0.0",
        model="qwen2.5:14b",
        embedding_model="nomic-embed-text",
        mock_llm=True,
        mock_rag=True,
    )
    assert data.status == "ok"
    assert data.mock_llm is True


def test_health_response_missing_required_field():
    with pytest.raises(ValidationError):
        HealthResponse(status="ok", version="1.0.0")


def test_api_response_success_wrapper():
    wrapped = ApiResponse[dict](code=200, data={"task_id": "abc"})
    assert wrapped.code == 200
    assert wrapped.data == {"task_id": "abc"}


def test_api_response_error_shape():
    wrapped = ApiResponse(code=400, msg="仅支持 Word RFQ 文件（.docx 或 .doc）")
    assert wrapped.code == 400
    assert wrapped.data is None
