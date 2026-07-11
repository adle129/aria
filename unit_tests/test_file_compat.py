import shutil
import sys
from pathlib import Path

import pytest

from app.file_compat import (
    FileCompatibilityError,
    resolve_case_insensitive,
)
from app.schemas.engagement import EngagementManifest
from app.services.ingest.engagement_preview import (
    build_engagement_preview,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RFQ = ROOT / "samples" / "rfq" / "mock_chassis_rfq.docx"
QA_TEMPLATE = ROOT / "backend" / "data" / "templates" / "qa_template.xlsx"


def test_manifest_drives_nested_windows_style_paths(tmp_path):
    if not SAMPLE_RFQ.exists() or not QA_TEMPLATE.exists():
        pytest.skip("sample files missing")
    folder = tmp_path / "engagement"
    nested = folder / "资料 空格"
    nested.mkdir(parents=True)
    shutil.copyfile(SAMPLE_RFQ, nested / "项目需求.DOCX")
    shutil.copyfile(QA_TEMPLATE, nested / "问题清单.XLSX")
    manifest = EngagementManifest.model_validate(
        {
            "engagement_id": "compat",
            "project_name": "Compatibility",
            "documents": [
                {
                    "path": r"资料 空格\项目需求.docx",
                    "doc_type": "RFQ",
                },
                {
                    "path": r"资料 空格\问题清单.xlsx",
                    "doc_type": "QA",
                },
            ],
        }
    )

    report = build_engagement_preview(folder, manifest)

    assert report["errors"] == []
    assert report["rfq"]["path"] == "资料 空格/项目需求.DOCX"
    assert report["qa"]["path"] == "资料 空格/问题清单.XLSX"


def test_fallback_detection_is_case_insensitive(tmp_path):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    folder = tmp_path / "engagement"
    folder.mkdir()
    shutil.copyfile(SAMPLE_RFQ, folder / "rfq_项目.DOCX")

    report = build_engagement_preview(folder)

    assert report["rfq"]["path"] == "rfq_项目.DOCX"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows 文件系统大小写不敏感，无法构造歧义目录项",
)
def test_case_insensitive_resolution_rejects_ambiguous_names(tmp_path):
    folder = tmp_path / "engagement"
    folder.mkdir()
    (folder / "RFQ.docx").write_bytes(b"one")
    (folder / "rfq.DOCX").write_bytes(b"two")

    with pytest.raises(FileCompatibilityError, match="歧义"):
        resolve_case_insensitive(folder, "rfq.docx")
