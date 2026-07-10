from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.disk_guard_service import DiskGuardService
from app.services.engagement_upload_service import EngagementUploadError


class UploadStreamService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.staging_root = (
            Path(settings.knowledge_base_path).parent / ".staging"
        )
        self.disk_guard = DiskGuardService(settings)

    def create_request_dir(self) -> Path:
        request_dir = self.staging_root / uuid.uuid4().hex
        request_dir.mkdir(parents=True, exist_ok=False)
        return request_dir

    def cleanup(self, request_dir: Path) -> None:
        shutil.rmtree(request_dir, ignore_errors=True)

    async def stage_upload(
        self,
        upload: Any,
        request_dir: Path,
        *,
        ordinal: int,
    ) -> tuple[str, Path, int]:
        original_name = str(upload.filename or "").strip()
        if not original_name:
            raise EngagementUploadError("上传文件缺少文件名")
        safe_name = Path(original_name.replace("\\", "/")).name
        if not safe_name or safe_name in {".", ".."}:
            raise EngagementUploadError("上传文件名非法")
        destination = request_dir / f"{ordinal:03d}-{safe_name}"
        total = 0
        try:
            with destination.open("xb") as output:
                while True:
                    chunk = await upload.read(
                        max(64 * 1024, self.settings.upload_stream_chunk_bytes)
                    )
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > self.settings.upload_max_archive_bytes:
                        raise EngagementUploadError(
                            f"{safe_name}: 文件超过 "
                            f"{self.settings.upload_max_archive_bytes // (1024 * 1024)}MB 限制"
                        )
                    self.disk_guard.assert_writable(
                        required_bytes=len(chunk)
                    )
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return safe_name, destination, total
