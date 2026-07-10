from __future__ import annotations

import errno
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

from app.config import Settings


class DiskUsage(NamedTuple):
    total: int
    used: int
    free: int


class DiskCapacityError(RuntimeError):
    def __init__(
        self,
        *,
        volume: str,
        required_bytes: int,
        available_bytes: int,
        usage_percent: float,
    ):
        self.volume = volume
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes
        self.usage_percent = usage_percent
        super().__init__(
            f"{volume} 空间不足：需要 {required_bytes} bytes，"
            f"可用 {available_bytes} bytes，使用率 {usage_percent:.1f}%"
        )

    def as_response(self) -> dict[str, Any]:
        return {
            "code": 507,
            "msg": "数据盘空间不足，写入操作已暂停；现有检索和下载仍可使用",
            "data": {
                "volume": self.volume,
                "required_bytes": self.required_bytes,
                "available_bytes": self.available_bytes,
                "usage_percent": round(self.usage_percent, 1),
                "action": "请清理或扩容数据盘后重试；如无法处理，请联系系统管理员",
            },
        }


class DiskGuardService:
    def __init__(
        self,
        settings: Settings,
        *,
        usage_provider: Callable[[str | Path], DiskUsage] | None = None,
        temp_path: str | Path | None = None,
    ):
        self.settings = settings
        self._usage_provider = usage_provider or shutil.disk_usage
        self.data_path = Path(settings.knowledge_base_path)
        self.temp_path = Path(temp_path or tempfile.gettempdir())

    def status(self) -> dict[str, dict[str, Any]]:
        return {
            "data_volume": self._volume_status("data", self.data_path),
            "temp_volume": self._volume_status("tmp", self.temp_path),
        }

    def assert_writable(
        self,
        *,
        required_bytes: int = 0,
        include_temp: bool = True,
    ) -> None:
        required = max(0, int(required_bytes)) + max(
            0, int(self.settings.disk_min_free_bytes)
        )
        checks = [("data", self.data_path)]
        if include_temp:
            checks.append(("tmp", self.temp_path))
        for name, path in checks:
            status = self._volume_status(name, path)
            if (
                status["write_protected"]
                or status["free_bytes"] < required
            ):
                raise DiskCapacityError(
                    volume=name,
                    required_bytes=required,
                    available_bytes=status["free_bytes"],
                    usage_percent=status["usage_percent"],
                )

    def normalize_os_error(
        self,
        exc: OSError,
        *,
        required_bytes: int = 0,
        volume: str = "data",
    ) -> DiskCapacityError | None:
        if exc.errno != errno.ENOSPC:
            return None
        path = self.temp_path if volume == "tmp" else self.data_path
        status = self._volume_status(volume, path)
        return DiskCapacityError(
            volume=volume,
            required_bytes=max(0, int(required_bytes)),
            available_bytes=status["free_bytes"],
            usage_percent=status["usage_percent"],
        )

    def _volume_status(
        self, name: str, path: Path
    ) -> dict[str, Any]:
        usage = self._usage_provider(self._existing_ancestor(path))
        total = max(0, int(usage.total))
        used = max(0, int(usage.used))
        free = max(0, int(usage.free))
        percent = (used / total * 100.0) if total else 100.0
        warning = percent >= float(self.settings.disk_warning_percent)
        protected = percent >= float(
            self.settings.disk_write_protect_percent
        )
        return {
            "volume": name,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "usage_percent": round(percent, 1),
            "warning": warning,
            "write_protected": protected,
        }

    @staticmethod
    def _existing_ancestor(path: Path) -> Path:
        current = path.expanduser()
        while not current.exists() and current != current.parent:
            current = current.parent
        return current
