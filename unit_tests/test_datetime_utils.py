from datetime import datetime, timezone

from app.utils.datetime_utils import to_api_utc_iso


def test_to_api_utc_iso_appends_z_for_naive_utc():
    dt = datetime(2026, 7, 9, 6, 0, 22, 181814)
    assert to_api_utc_iso(dt) == "2026-07-09T06:00:22.181814Z"
