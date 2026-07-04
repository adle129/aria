from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.services.demo_sample_service import (
    ALLOWED_DEMO_RFQ_FILENAMES,
    list_demo_rfq_samples,
    resolve_demo_rfq_file,
)


@pytest.fixture
def samples_dir(tmp_path: Path) -> Path:
    rfq_dir = tmp_path / "rfq"
    rfq_dir.mkdir()
    (rfq_dir / "mock_chassis_rfq.docx").write_bytes(b"mock")
    return rfq_dir


def test_list_demo_rfq_samples_only_existing_files(samples_dir: Path) -> None:
    settings = Settings(samples_rfq_path=str(samples_dir))
    items = list_demo_rfq_samples(settings)
    assert len(items) == 1
    assert items[0]["filename"] == "mock_chassis_rfq.docx"
    assert items[0]["download_url"].endswith("/mock_chassis_rfq.docx")


def test_resolve_demo_rfq_file_rejects_unknown_filename(samples_dir: Path) -> None:
    settings = Settings(samples_rfq_path=str(samples_dir))
    with pytest.raises(HTTPException) as exc:
        resolve_demo_rfq_file(settings, "evil.docx")
    assert exc.value.status_code == 404


def test_resolve_demo_rfq_file_rejects_path_traversal(samples_dir: Path) -> None:
    settings = Settings(samples_rfq_path=str(samples_dir))
    with pytest.raises(HTTPException) as exc:
        resolve_demo_rfq_file(settings, "../secrets.docx")
    assert exc.value.status_code == 404
    assert "evil" not in ALLOWED_DEMO_RFQ_FILENAMES


def test_resolve_demo_rfq_file_missing_file(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    settings = Settings(samples_rfq_path=str(empty_dir))
    with pytest.raises(HTTPException) as exc:
        resolve_demo_rfq_file(settings, "mock_chassis_rfq.docx")
    assert exc.value.status_code == 404
    assert "未就绪" in str(exc.value.detail)
