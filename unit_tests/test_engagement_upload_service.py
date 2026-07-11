import io
import json
import stat
import zipfile
from pathlib import Path

import pytest

from app.config import Settings
from app.services.engagement_upload_service import (
    EngagementUploadConflict,
    EngagementUploadError,
    EngagementUploadService,
)

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"
QA_TEMPLATE = Path(__file__).resolve().parents[1] / "backend" / "data" / "templates" / "qa_template.xlsx"


@pytest.fixture
def upload_service(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    return EngagementUploadService(Settings(knowledge_base_path=str(kb)))


def _make_loose_pack_zip(folder_name: str, rfq_bytes: bytes, qa_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{folder_name}/RFQ_mock.docx", rfq_bytes)
        zf.writestr(f"{folder_name}/Q_A_mock.xlsx", qa_bytes)
    return buf.getvalue()


def test_upload_loose_files_requires_engagement_id(upload_service):
    with pytest.raises(EngagementUploadError, match="engagement_id"):
        upload_service.upload_batch(loose_files=[("RFQ.docx", b"x")])


def test_upload_loose_files_writes_manifest_and_reports_missing_quote(upload_service):
    if not SAMPLE_RFQ.exists() or not QA_TEMPLATE.exists():
        pytest.skip("sample files missing")
    result = upload_service.upload_loose_files(
        "demo_engagement",
        [
            ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes()),
            ("Q_A_mock.xlsx", QA_TEMPLATE.read_bytes()),
        ],
    )
    assert result["engagement_id"] == "demo_engagement"
    assert result["status"] == "stored"
    assert result["stored"] is True
    assert result["indexable"] is True
    assert result["tier"] == "silver"
    assert "quote_manpower" in result["missing"]
    manifest = json.loads(
        (Path(upload_service.kb_root) / "demo_engagement" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["engagement_id"] == "demo_engagement"


def test_upload_zip_pack_extracts_engagement(upload_service):
    if not SAMPLE_RFQ.exists() or not QA_TEMPLATE.exists():
        pytest.skip("sample files missing")
    payload = _make_loose_pack_zip("zip_engagement", SAMPLE_RFQ.read_bytes(), QA_TEMPLATE.read_bytes())
    result = upload_service.upload_zip_pack("zip_engagement.zip", payload)
    assert result["engagement_id"] == "zip_engagement"
    assert (Path(upload_service.kb_root) / "zip_engagement" / "RFQ_mock.docx").is_file()


def test_upload_rfq_only_is_stored_as_indexable_copper(upload_service):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    result = upload_service.upload_loose_files(
        "copper_engagement",
        [("RFQ_mock.docx", SAMPLE_RFQ.read_bytes())],
    )

    assert result["status"] == "stored"
    assert result["tier"] == "copper"
    assert result["indexable"] is True
    assert result["missing"] == ["qa", "quote_manpower"]
    assert len(result["automation_impacts"]) == 2


def test_duplicate_engagement_requires_explicit_replace(upload_service):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    files = [("RFQ_mock.docx", SAMPLE_RFQ.read_bytes())]
    upload_service.upload_loose_files("duplicate_engagement", files)

    with pytest.raises(EngagementUploadConflict, match="替换"):
        upload_service.upload_loose_files("duplicate_engagement", files)


def test_replace_existing_engagement_atomically_swaps_files(upload_service):
    if not SAMPLE_RFQ.exists() or not QA_TEMPLATE.exists():
        pytest.skip("sample files missing")
    upload_service.upload_loose_files(
        "replace_engagement",
        [
            ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes()),
            ("Q_A_mock.xlsx", QA_TEMPLATE.read_bytes()),
        ],
    )

    result = upload_service.upload_loose_files(
        "replace_engagement",
        [("RFQ_replacement.docx", SAMPLE_RFQ.read_bytes())],
        replace_existing=True,
    )
    target = Path(upload_service.kb_root) / "replace_engagement"

    assert result["tier"] == "copper"
    assert (target / "RFQ_replacement.docx").is_file()
    assert not (target / "Q_A_mock.xlsx").exists()
    assert not list(Path(upload_service.kb_root).glob(".backup-*"))
    assert not list(Path(upload_service.kb_root).glob(".staging-*"))


def test_upload_batch_rejects_more_than_five_zips(upload_service):
    zips = [("a.zip", b"PK\x05\x06")] * 6
    with pytest.raises(EngagementUploadError, match="5"):
        upload_service.upload_batch(zip_files=zips)


@pytest.mark.parametrize(
    "member_name",
    ["../escape.txt", r"..\escape.txt", "/absolute.txt", "C:/drive.txt"],
)
def test_zip_rejects_path_escape_and_cleans_staging(
    upload_service, member_name
):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as zf:
        zf.writestr(member_name, b"blocked")

    with pytest.raises(EngagementUploadError, match="非法路径"):
        upload_service.upload_zip_pack("unsafe.zip", payload.getvalue())

    assert not (Path(upload_service.kb_root) / "unsafe").exists()
    staging = Path(upload_service.kb_root).parent / ".staging"
    assert not [p for p in staging.iterdir()] if staging.exists() else True


def test_zip_rejects_symlink_entry(upload_service):
    payload = io.BytesIO()
    link = zipfile.ZipInfo("project/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(payload, "w") as zf:
        zf.writestr(link, "target")

    with pytest.raises(EngagementUploadError, match="链接"):
        upload_service.upload_zip_pack("links.zip", payload.getvalue())


def test_zip_rejects_abnormal_compression_ratio(upload_service):
    payload = io.BytesIO()
    with zipfile.ZipFile(
        payload, "w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        zf.writestr("project/RFQ_bomb.docx", b"0" * 100_000)

    with pytest.raises(EngagementUploadError, match="压缩比"):
        upload_service.upload_zip_pack("bomb.zip", payload.getvalue())


def test_zip_rejects_too_many_entries(tmp_path):
    service = EngagementUploadService(
        Settings(
            knowledge_base_path=str(tmp_path / "kb"),
            upload_max_entries=1,
        )
    )
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as zf:
        zf.writestr("project/a.txt", b"a")
        zf.writestr("project/b.txt", b"b")

    with pytest.raises(EngagementUploadError, match="条目数"):
        service.upload_zip_pack("many.zip", payload.getvalue())


def test_zip_rejects_file_directory_path_conflict(upload_service):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as zf:
        zf.writestr("project/RFQ.docx", b"file")
        zf.writestr("project/RFQ.docx/nested.txt", b"nested")

    with pytest.raises(EngagementUploadError, match="路径冲突"):
        upload_service.upload_zip_pack("conflict.zip", payload.getvalue())


def test_loose_upload_normalizes_nfc_and_preserves_original_name(
    upload_service
):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    original = "RFQ_Cafe\u0301.DOCX"

    upload_service.upload_loose_files(
        "unicode_engagement",
        [(original, SAMPLE_RFQ.read_bytes())],
    )

    target = Path(upload_service.kb_root) / "unicode_engagement"
    assert (target / "RFQ_Café.DOCX").is_file()
    manifest = json.loads(
        (target / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["documents"][0]["path"] == "RFQ_Café.DOCX"
    assert manifest["documents"][0]["original_filename"] == original


def test_loose_upload_rejects_case_insensitive_name_collision(
    upload_service
):
    with pytest.raises(EngagementUploadError, match="冲突"):
        upload_service.upload_loose_files(
            "collision_engagement",
            [
                ("RFQ.docx", b"first"),
                ("rfq.DOCX", b"second"),
            ],
        )


def test_upload_returns_domain_error_for_invalid_manifest(upload_service):
    manifest = json.dumps(
        {
            "engagement_id": "invalid_manifest",
            "project_name": "Invalid",
            "documents": [
                {"path": "legacy.xls", "doc_type": "qa"}
            ],
        }
    ).encode()

    with pytest.raises(
        EngagementUploadError, match="manifest.json 校验失败"
    ):
        upload_service.upload_loose_files(
            "invalid_manifest",
            [("MANIFEST.JSON", manifest), ("legacy.xls", b"fake")],
        )
