from typing import Any, Literal

from pydantic import BaseModel, Field


class ConfirmDimensionsRequest(BaseModel):
    baseline_version: str | None = None
    items: list[dict[str, Any]] | None = None
    custom_items: list[dict[str, Any]] | None = None
    comparison_dimensions: list[dict[str, Any]] | None = None


class RFQTaskUpdateRequest(BaseModel):
    status: Literal["in_review", "approved", "exported"] | None = None
    comparison_table: dict[str, Any] | None = None
    dimension_draft: dict[str, Any] | None = None
    confirmed: bool | None = None
