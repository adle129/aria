import pytest

from app.api.deps import block_r1_undelivered_milestone, is_r1_profile
from app.config import Settings
from fastapi import HTTPException


def test_is_r1_profile():
    assert is_r1_profile(Settings(aria_ui_profile="r1")) is True
    assert is_r1_profile(Settings(aria_ui_profile="experience")) is False


def test_block_r1_undelivered_raises():
    with pytest.raises(HTTPException) as exc:
        block_r1_undelivered_milestone(Settings(aria_ui_profile="r1"))
    assert exc.value.status_code == 404


def test_block_r1_undelivered_allows_experience():
    block_r1_undelivered_milestone(Settings(aria_ui_profile="experience"))
