import json
from pathlib import Path

import pytest

from app.services.engagement_manifest_service import infer_manifest_from_folder, load_manifest_file
from app.schemas.engagement import EngagementManifest


def test_load_manifest_file(tmp_path):
    folder = tmp_path / "2023_chassis"
    folder.mkdir()
    manifest = {
        "engagement_id": "2023_chassis",
        "project_name": "2023 Chassis Integration",
        "customer": "OEM-A",
        "year": 2023,
        "functions": ["Chassis", "PM"],
        "documents": [
            {"path": "rfq.docx", "doc_type": "rfq"},
            {"path": "qa.xlsx", "doc_type": "qa"},
        ],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    loaded = load_manifest_file(folder / "manifest.json")
    assert loaded.engagement_id == "2023_chassis"
    assert len(loaded.documents) == 2


def test_infer_manifest_from_folder(tmp_path):
    folder = tmp_path / "demo_engagement"
    folder.mkdir()
    (folder / "RFQ_sample.docx").write_bytes(b"fake")
    (folder / "Q_A_sample.xlsx").write_bytes(b"fake")
    manifest = infer_manifest_from_folder(folder)
    assert manifest.engagement_id == "demo_engagement"
    doc_types = {d.doc_type for d in manifest.documents}
    assert "rfq" in doc_types
    assert "qa" in doc_types


def test_manifest_normalizes_windows_path_unicode_and_role():
    manifest = EngagementManifest.model_validate(
        {
            "engagement_id": "兼容项目",
            "project_name": "Windows Upload",
            "documents": [
                {
                    "path": "资料\\RFQ_Cafe\u0301.DOCX",
                    "doc_type": "RFQ",
                    "original_filename": "RFQ_Cafe\u0301.DOCX",
                }
            ],
        }
    )

    document = manifest.documents[0]
    assert document.path == "资料/RFQ_Café.DOCX"
    assert document.doc_type == "rfq"
    assert document.original_filename == "RFQ_Cafe\u0301.DOCX"


@pytest.mark.parametrize(
    "path",
    [
        "../RFQ.docx",
        r"C:\RFQ.docx",
        r"\\server\share\RFQ.docx",
        "/tmp/RFQ.docx",
    ],
)
def test_manifest_rejects_unsafe_paths(path):
    with pytest.raises(ValueError, match="POSIX"):
        EngagementManifest.model_validate(
            {
                "engagement_id": "unsafe",
                "project_name": "Unsafe",
                "documents": [{"path": path, "doc_type": "rfq"}],
            }
        )


def test_manifest_rejects_legacy_xls_with_conversion_guidance():
    with pytest.raises(ValueError, match="convert.*xlsx"):
        EngagementManifest.model_validate(
            {
                "engagement_id": "legacy",
                "project_name": "Legacy",
                "documents": [
                    {"path": "Q_A.xls", "doc_type": "qa"}
                ],
            }
        )


def test_update_manifest_metadata_writes_business_fields(tmp_path):
    from app.services.engagement_manifest_service import (
        metadata_fields_complete,
        resolve_manifest,
        update_manifest_metadata,
    )

    folder = tmp_path / "meta_eng"
    folder.mkdir()
    (folder / "RFQ_sample.docx").write_bytes(b"fake")
    updated = update_manifest_metadata(
        folder,
        project_name="Meta Project",
        customer="OEM-B",
        year=2024,
        functions=["Chassis", "chassis", "PM"],
    )
    assert updated.project_name == "Meta Project"
    assert updated.customer == "OEM-B"
    assert updated.year == 2024
    assert updated.functions == ["Chassis", "PM"]
    assert metadata_fields_complete(updated) is True
    reloaded = resolve_manifest(folder)
    assert reloaded.functions == ["Chassis", "PM"]
    assert (folder / "manifest.json").is_file()


def test_update_manifest_metadata_can_clear_optional_fields(tmp_path):
    from app.services.engagement_manifest_service import update_manifest_metadata

    folder = tmp_path / "clear_eng"
    folder.mkdir()
    (folder / "RFQ_sample.docx").write_bytes(b"fake")
    update_manifest_metadata(
        folder,
        project_name="Keep Name",
        customer="OEM",
        year=2023,
        functions=["PM"],
    )
    cleared = update_manifest_metadata(
        folder,
        customer=None,
        year=None,
        functions=[],
    )
    assert cleared.project_name == "Keep Name"
    assert cleared.customer is None
    assert cleared.year is None
    assert cleared.functions == []
