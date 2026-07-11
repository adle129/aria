import pytest

from app.config import Settings
from app.services.disk_guard_service import DiskCapacityError
from app.services.engagement_upload_service import EngagementUploadError
from app.services.upload_stream_service import UploadStreamService


class FakeUpload:
    def __init__(self, filename: str, payload: bytes):
        self.filename = filename
        self.payload = payload
        self.offset = 0
        self.read_sizes: list[int] = []

    async def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


@pytest.mark.asyncio
async def test_upload_is_streamed_to_data_staging(tmp_path):
    service = UploadStreamService(
        Settings(
            knowledge_base_path=str(tmp_path / "knowledge_base"),
            upload_stream_chunk_bytes=64 * 1024,
        )
    )
    request_dir = service.create_request_dir()
    upload = FakeUpload("RFQ.docx", b"x" * (150 * 1024))

    name, path, size = await service.stage_upload(
        upload, request_dir, ordinal=1
    )

    assert name == "RFQ.docx"
    assert size == 150 * 1024
    assert path.read_bytes() == upload.payload
    assert len(upload.read_sizes) >= 3
    service.cleanup(request_dir)
    assert not request_dir.exists()


@pytest.mark.asyncio
async def test_oversized_stream_removes_partial_file(tmp_path):
    service = UploadStreamService(
        Settings(
            knowledge_base_path=str(tmp_path / "knowledge_base"),
            upload_max_archive_bytes=100,
            upload_stream_chunk_bytes=64 * 1024,
        )
    )
    request_dir = service.create_request_dir()

    with pytest.raises(EngagementUploadError, match="超过"):
        await service.stage_upload(
            FakeUpload("large.zip", b"x" * 101),
            request_dir,
            ordinal=1,
        )

    assert not list(request_dir.iterdir())


@pytest.mark.asyncio
async def test_capacity_failure_removes_partial_file(
    tmp_path, monkeypatch
):
    service = UploadStreamService(
        Settings(knowledge_base_path=str(tmp_path / "knowledge_base"))
    )
    request_dir = service.create_request_dir()

    def fail_capacity(*_args, **_kwargs):
        raise DiskCapacityError(
            volume="data",
            required_bytes=10,
            available_bytes=1,
            usage_percent=99,
        )

    monkeypatch.setattr(
        service.disk_guard, "assert_writable", fail_capacity
    )
    with pytest.raises(DiskCapacityError):
        await service.stage_upload(
            FakeUpload("RFQ.docx", b"content"),
            request_dir,
            ordinal=1,
        )

    assert not list(request_dir.iterdir())
