import errno

import pytest

from app.config import Settings
from app.services.disk_guard_service import (
    DiskCapacityError,
    DiskGuardService,
    DiskUsage,
)


def _guard(*, used: int, free: int, min_free: int = 0) -> DiskGuardService:
    total = used + free
    return DiskGuardService(
        Settings(
            knowledge_base_path=".",
            disk_warning_percent=80,
            disk_write_protect_percent=90,
            disk_min_free_bytes=min_free,
        ),
        usage_provider=lambda _path: DiskUsage(total, used, free),
        temp_path=".",
    )


def test_status_marks_warning_without_write_protection():
    status = _guard(used=85, free=15).status()["data_volume"]

    assert status["usage_percent"] == 85.0
    assert status["warning"] is True
    assert status["write_protected"] is False


def test_write_protection_blocks_mutation():
    guard = _guard(used=91, free=9)

    with pytest.raises(DiskCapacityError) as caught:
        guard.assert_writable(include_temp=False)

    assert caught.value.volume == "data"
    assert caught.value.as_response()["code"] == 507


def test_required_space_includes_reserved_free_bytes():
    guard = _guard(used=50, free=50, min_free=20)

    with pytest.raises(DiskCapacityError) as caught:
        guard.assert_writable(required_bytes=31, include_temp=False)

    assert caught.value.required_bytes == 51


def test_enospc_is_normalized_but_other_os_errors_are_not():
    guard = _guard(used=50, free=50)

    normalized = guard.normalize_os_error(
        OSError(errno.ENOSPC, "disk full"), required_bytes=10
    )

    assert isinstance(normalized, DiskCapacityError)
    assert guard.normalize_os_error(OSError(errno.EACCES, "denied")) is None
