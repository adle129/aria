import pytest

from app.config import Settings
from app.services.rfq_analysis_service import RFQAnalysisService
from app.services.rfq_upload import (
    RFQ_UPLOAD_REJECT_MSG,
    is_allowed_rfq_filename,
    validate_rfq_upload_filename,
)


def test_is_allowed_rfq_filename():
    assert is_allowed_rfq_filename("RFQ.docx") is True
    assert is_allowed_rfq_filename("legacy.doc") is True
    assert is_allowed_rfq_filename("RFQ.DOC") is True
    assert is_allowed_rfq_filename("bad.pdf") is False
    assert is_allowed_rfq_filename("bad.txt") is False


def test_validate_rfq_upload_filename_rejects_pdf():
    with pytest.raises(ValueError, match=RFQ_UPLOAD_REJECT_MSG):
        validate_rfq_upload_filename("rfq.pdf")


def test_save_upload_accepts_doc_extension(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_PATH", str(tmp_path))
    from app.config import get_settings

    get_settings.cache_clear()
    svc = RFQAnalysisService(get_settings())
    file_id, stored_path = svc.save_upload("legacy_rfq.doc", b"fake-doc-bytes")
    assert stored_path.endswith("_legacy_rfq.doc")
    assert file_id


def test_save_upload_rejects_txt(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_PATH", str(tmp_path))
    from app.config import get_settings

    get_settings.cache_clear()
    svc = RFQAnalysisService(get_settings())
    with pytest.raises(ValueError, match=RFQ_UPLOAD_REJECT_MSG):
        svc.save_upload("notes.txt", b"hello")
